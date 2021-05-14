# ACM Private Certificate Renewal

## AWS ACM Privae Certs Setup

**Account A** - It has Root CA and Suborbinates through which Private certs are requested. Private Certs in Account A are eligible for automatic renewal by AWS.

**Account B** - Private certs requested in Account A are exported and re-imported into Account B. Account B private certs are eventually used by  applications deployed in account B. 

- Since these privatecerts are imported, they are not eligible for automatic renewal by AWS.

- Every time the Account B private certs approaches their expiry date, users have to manually request a new private cert in AccountA and re-import into Account B.

- To automate the manually work, lambda is being deployed into Account B which is in turn triggered by a Cloud Watch Event bridge every 90 days. Lambda needs to have proper IAM permissions to allow cloudwatch and cross-account (Account B -> Account A -> Account B) Acess. 

## Lambda Functionality
- Step1 - Looks for private certs "in use" in "Account B" whose domain name ends in ".example.local".

- Step2 - Checks if their expiry is in next 45 days. if yes - Grabs the Domain name of the expiring certs in "Account B".

- Step3 - Goes to "Account A" and does the following.
  - Requests a private certificate.
  - Selects subordinate CA.
  - Adds domain name similar to the one expiring in "Account B" (refer to Step2).
  - Exports the newly requested Private key - If done via AWS console, it would ask to Enter a passphrase and confirm it for encrypting the private key. It then generates Certificate body, Certificate chain and Certificate private key.

- Step 4 - Now lambda returns to "Account B" and reimports certificate to the expiring cert (The one grabbed in Step2) - this step requires Certificate body, Certificate chain and Certificate private key generated in "Account A" (refer to step 3).

**Note** - This Readme is mainly focused on Python Code workflow, hence not providing details on IAM and Cloudwatch triggers.
### Reference - 
https://docs.aws.amazon.com/acm/latest/userguide/managed-renewal.html
