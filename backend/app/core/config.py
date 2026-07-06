from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", protected_namespaces=('settings_',))

    supabase_url: str = ""
    supabase_service_key: str = ""
    port: int = 8000
    model_path: str = "./models/phi-4-mini-Q4_K_M.gguf"
    n_ctx: int = 4096
    n_gpu_layers: int = 0
    frontend_url: str = "http://localhost:5173"
    hf_token: str = ""
    gemini_api_key: str = ""
    
    llm_provider: str = "openrouter"
    openrouter_api_key: str = ""
    
    # Model Registry
    orchestrator_model: str = "meta-llama/llama-3.1-8b-instruct"
    tutor_model: str = "deepseek/deepseek-r1-distill-qwen-32b"
    research_model: str = "meta-llama/llama-3.1-8b-instruct"
    visual_model: str = "meta-llama/llama-3.1-8b-instruct"
    quiz_model: str = "meta-llama/llama-3.1-8b-instruct"
    critic_model: str = "meta-llama/llama-3.1-8b-instruct"

settings = Settings()
