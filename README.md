# kalshi-starter-code-python
Example python code for accessing api-authenticated endpoints on [Kalshi](https://kalshi.com). This is not an SDK. 

## Installation 
Install requirements.txt in a virtual environment of your choice and execute main.py from within the repo.

```
pip install -r requirements.txt
python main.py
```
## Troubleshooting

Here are a few common issues you might encounter when running the starter code and how to fix them.

### 1. `ModuleNotFoundError` for Kalshi SDK

If you see an error like:

- `ModuleNotFoundError: No module named 'kalshi_python'`

Make sure you installed the SDK in the same virtual environment where you are running the scripts:

~~~bash
pip install kalshi-python
~~~

Then retry the command from inside the activated virtual environment.

### 2. Authentication or 401 errors

If API calls fail with authentication errors:

- Double-check that your API key and private key path are correct.
- Confirm that the environment variables you use in this project match those shown in the Kalshi docs.
- Make sure the private key file is readable by your user and not empty.

### 3. Environment problems

If you are unsure whether your environment is configured correctly, try this quick checklist:

1. Activate your virtual environment.
2. Run `python --version` and confirm it matches the version recommended in this repository.
3. Run `pip list` and check that `kalshi-python` is installed.
4. Run the simplest example script first before trying more advanced ones.

If issues persist, consider opening an issue with:

- The command you ran
- The full traceback (redacted of any secrets)
- Information about your OS and Python version
