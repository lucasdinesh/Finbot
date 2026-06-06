import config


class TestConfigConstants:
    def test_default_categories(self):
        assert len(config.DEFAULT_CATEGORIES) >= 5
        assert "Alimentação" in config.DEFAULT_CATEGORIES
        assert "Transporte" in config.DEFAULT_CATEGORIES

    def test_token_exists(self):
        assert isinstance(config.TOKEN, str)

    def test_database_default(self):
        assert config.DATABASE is not None

    def test_max_date_interval_default(self):
        assert config.MAX_DATE_INTERVAL > 0

    def test_llm_enabled_is_bool(self):
        assert isinstance(config.LLM_ENABLED, bool)

    def test_llm_user_prompt_contains_nao_especificado(self):
        assert "Não especificado" in config.LLM_USER_PROMPT

    def test_llm_system_prompt(self):
        assert "comprovantes" in config.LLM_SYSTEM_PROMPT.lower()

    def test_local_mode_default(self):
        assert isinstance(config.local_mode, bool)
