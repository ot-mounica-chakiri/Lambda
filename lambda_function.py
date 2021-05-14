from __future__ import print_function
import operator
import base64
import datetime
from datetime import date, datetime
from Crypto.PublicKey import RSA
import boto3


########################################################################################################################
# CROSS ACCOUNT ROLE ASSUMPTION. THIS BLOCK OF CODE ALLOWS LAMBDA TO ASSUME A ROLE FROM OT-NETWORK-SHAREDSERVICE ACCOUNT
########################################################################################################################

REGION_NAME = "us-east-1"

def assume_role(arn, session=boto3, region_name='us-east-1', **sts_client_assume_role_kwargs):
    sts_client = session.client('sts', region_name=region_name)

    #Set kwargs
    sts_client_assume_role_kwargs['RoleArn'] = arn
    sts_client_assume_role_kwargs['RoleSessionName'] = 'socks_sts_assume_role'

    try:
        response = sts_client.assume_role(**sts_client_assume_role_kwargs)
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"ERROR: {error_code}")
        raise e
    else:
        session = boto3.Session(
                aws_access_key_id=response['Credentials']['AccessKeyId'],
                aws_secret_access_key=response['Credentials']['SecretAccessKey'],
                aws_session_token=response['Credentials']['SessionToken'])
        return session

#########################################################################################################        
# STEP 1 - LOOK  FOR PRIVATE CERTS ISSUED IN THIS ACCOUNT WHOSE DOMAIN NAME ENDS WITH ".onetechaws.otlocal".
# STEP 2 - CHECK IF THE EXPIRY IS IN NEXT 45 DAYS. IF YES GRAB THE DOMAIN NAME.
#########################################################################################################
global sorted_cert,AccountBdomainname
def lambda_handler(event, context):
    acm_client  = boto3.client('acm')
    #listing issues certs in this account
    response = acm_client.list_certificates(CertificateStatuses=['ISSUED'])
    #parsing the output given by response
    response = response['CertificateSummaryList']
    for i in range(len(response)):
        if "onetechaws.otlocal" in response[i]["DomainName"]:
            AccountBcertarns = [response[i]["CertificateArn"]]
            AccountBdomains = [response[i]["DomainName"]]
            for j in range(len(AccountBcertarns)):
                AccountBdomainname = AccountBdomains[j]
                print(AccountBdomainname)
                response2 = acm_client.describe_certificate(CertificateArn=AccountBcertarns[j])
                # checking for number of days left for the cert to expire
                response2 = response2['Certificate']
                expirydate = response2['NotAfter']
                expirydate = str(expirydate.strftime('%Y%m%d'))
                today = date.today()
                today = str(today.strftime('%Y%m%d'))
                dateofexpiry = datetime.strptime(expirydate, "%Y%m%d")
                presentdate = datetime.strptime(today, "%Y%m%d")
                numberofdaysleft = abs((dateofexpiry - presentdate).days)
                # To renew certs expiring soon
                if numberofdaysleft<=45:
                    print ("Expiry approaching")
                    # Go To Account A (network account)
                    session = assume_role(arn='arn:aws:iam::131396953364:role/ot-certrenewal-crossaccount-role')
                    acm_client1  = session.client('acm')
                    # To request new Cert with same domain name in Network A
                    response3 = acm_client1.request_certificate(DomainName=AccountBdomainname, CertificateAuthorityArn='arn:aws:acm-pca:us-east-1:131396953364:certificate-authority/22407152-8d8f-441f-b720-1e19f5f72ab0')
                    sorted_cert = response3["CertificateArn"]
                    print(sorted_cert)
                    # To export the new cert in Network A
                    exportingcertdetails(sorted_cert,AccountBdomainname)
                else:
                    print("not approaching expiry ")

def exportingcertdetails(AccountAlatestcertarn,AccountBdomainname):
    session = assume_role(arn='arn:aws:iam::131396953364:role/ot-certrenewal-crossaccount-role')
    acm_client  = session.client('acm')
    response = acm_client.export_certificate(CertificateArn=AccountAlatestcertarn,Passphrase='test')
    cert = bytes(response['Certificate'], 'utf-8')
    certchain = bytes(response['CertificateChain'], 'utf-8')
    encryptedkey = response['PrivateKey']
    encryptedkey = bytes(encryptedkey, 'utf-8')
    decrypted_key = RSA.importKey(encryptedkey, passphrase="test").export_key()
    importingcertcredentials(cert,certchain,decrypted_key,AccountBdomainname)

def importingcertcredentials(a,b,c,d):
    acm_client  = boto3.client('acm')
    #listing issues certs in this account
    response = acm_client.list_certificates(CertificateStatuses=['ISSUED'])
    response = response['CertificateSummaryList']
    for i in range(len(response)):
        if d in response[i]["DomainName"]:
            AccountBcertarns = [response[i]["CertificateArn"]]
            AccountBdomains = [response[i]["DomainName"]]
            print(AccountBdomains)
            print(AccountBcertarns)
            #Re-Importing to expiring certs in this Account B
            response1 = acm_client.import_certificate(CertificateArn=response[i]["CertificateArn"],Certificate=a,PrivateKey=c,CertificateChain=b)
    print("Imported")