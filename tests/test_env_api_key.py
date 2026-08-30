import os
from dotenv import load_dotenv
from app.config.hospital_profile import load_hospital_profile
from app.llm.client import LLMClient
from app.privacy.llm_gateway import LLMClientConfig

def test_llm_client_uses_env_file():
    # Load the .env file that we just modified
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    load_dotenv(env_path, override=True)
    
    # Load the default profile to get the expected env var name (GROQ_API_KEY)
    profile = load_hospital_profile("default")
    config = LLMClientConfig(
        provider=profile.llm.provider,
        model=profile.llm.model,
        api_key_env_var=profile.llm.api_key_env_var
    )
    
    client = LLMClient(config)
    
    # The client should successfully retrieve the key from os.environ
    # which was populated by dotenv from the .env file
    assert client._api_key() == "test_key_from_env_file"
