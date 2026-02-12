# kalshi-starter-code-python
Example python code for accessing api-authenticated endpoints on [Kalshi](https://kalshi.com). This is not an SDK. 

## Installation 
Install requirements.txt in a virtual environment of your choice and execute main.py from within the repo.

```
pip install -r requirements.txt
python main.py
```
### Troubleshooting

- **Authentication Error**: Double-check your email and password in the `.env` file. Ensure you are using the correct URL for Demo or Live environments.
- **ModuleNotFoundError**: Run `pip install -r requirements.txt` to ensure all necessary libraries are installed.
- **Rate Limiting**: If you receive a 429 error, reduce the frequency of your API requests.
