from dino.config import ConfigKeys
from dino.enrich import IEnricher


class TitleEnrichment(IEnricher):
    def __init__(self, env):
        self.env = env
        enrich_config = env.config.get(ConfigKeys.ENRICH, dict())
        title_config = enrich_config.get(ConfigKeys.TITLE, dict())
        self.title_prefix = title_config.get(ConfigKeys.PREFIX, '')

    def __call__(self, *args, **kwargs) -> dict:
        data = args[0]
        data['title'] = '{}{}'.format(self.title_prefix, data.get(ConfigKeys.VERB, ''))
        return data
