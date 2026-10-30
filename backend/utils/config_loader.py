import json
import os
from pathlib import Path

# Define the path relative to this file
BASE_DIR = Path(__file__).resolve().parent.parent   # directory backend/
print(f"BASE_DIR: {str(BASE_DIR)}")

# ==================== METHOD-1: Using pathlib to define paths ==================== 
def load_config_from_json(config_file: str):
    """ Load configuration from json config file """
    CONFIG_FILE = BASE_DIR / config_file
    # print(f"CONFIG FILEPATH: {CONFIG_FILE}")
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"Config file not found at {CONFIG_FILE}")
    
    with open(CONFIG_FILE, "r") as f:
        data = json.load(f)
        return data

# ==================== METHOD-2: Using Environment variables ==================== 
def get_env_variable(var_name: str, default_value=None):
    """ get environment variable, or default value

    Args:
        var_name (str): name of env variable
        default_value (_type_, optional): Default value. Defaults to None.

    Raises:
        EnvironmentError: thrown when env variable not defined

    Returns:
        Any: value of env variable
    """
    value = os.getenv(var_name, default_value)
    if value is None:
        raise EnvironmentError(f"Required environment variable: {var_name}")
    return value

def load_config_from_env():
    """ Load configuration from environment variables """
    raise NotImplementedError("Loading config from env variables not implemented yet. Please use config.json for now.")

# =================== Load configuration ====================
# def load_configuration(config_file: str = "config.json"):
def load_configuration(*args, **kwargs):
    """
    Load configuration settings from environment variables or config file.    
    Returns:
        dict: configs as a dictionary
    """    
    config_settings = {}
    try: 
        config_settings = load_config_from_env()  # from env variables if available
    except Exception as e:
        config_file = kwargs.get("config_file", "config.json")      # file name is a keyword argument
        print(f"#### Environment variables missing. Falling back to {config_file} \nError: {e}")
        config_settings = load_config_from_json(config_file)     # from config_file
    config_settings["BASE_DIR"] = str(BASE_DIR)   # add BASE_DIR object to config_settings
    print(f"##### loaded config_settings.....")
    # print(config_settings)
    return config_settings
