## Disclaimer
This documentation is written as of 06/17/2014. JIRA 6.3 implements OAuth1. Most of this doc would need to be revised when JIRA switches to OAuth2.

## Steps
1. Generate RSA public/private key pair
    ```
    # This will create a 2048 length RSA private key
    $openssl genrsa -out mykey.pem 2048
    ```
    
    ```
    # Now, create the public key associated with that private key
    openssl rsa -in mykey.pem -pubout
    ```
2. Generate a consumer key. You can use python uuid.uuid4() to do this.
3. Configure JIRA for external access:
     * Go to AppLinks section of your JIRA - https://JIRA_SERVER/plugins/servlet/applinks/listApplicationLinks
     * Create a Generic Application with some fake URL
     * Click Edit, hit IncomingAuthentication. Plug in the consumer key and RSA public key you generated.
4. Get access token using this [script](https://github.com/lakshmi-kannan/jira-oauth-access-token-generator/blob/master/generate_access_token.py)
5. Plug in the access token and access secret into the sensor or action. You are good to make JIRA calls. Note: OAuth token expires. You'll have to repeat the process based on the expiry date. 
