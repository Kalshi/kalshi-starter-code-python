Markdown
# kalshi-starter-code-python
Example python code for accessing api-authenticated endpoints on [Kalshi](https://kalshi.com). This is not an SDK. 

## Installation 
Install requirements.txt in a virtual environment of your choice and execute main.py from within the repo.

pip install -r requirements.txt
python main.py


## Configuration

Create a `.env` file or export the following variables before running the example:

```text
KALSHI_ENV=demo
DEMO_KEYID=your-demo-key-id
DEMO_KEYFILE=~/path/to/demo-private-key.pem
Use the corresponding PROD_KEYID, PROD_KEYFILE, and optional PROD_KEY_PASSWORD variables when KALSHI_ENV=prod. The private-key file must remain outside version control; encrypted PEM files can be used with the matching *_KEY_PASSWORD variable.
