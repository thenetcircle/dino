from dino.config import ConfigKeys
from dino.enrich import IEnricher
from dino.environ import GNEnvironment


class TopicEnrichment(IEnricher):
    def __init__(self, env: GNEnvironment):
        self.env = env
        enrich_config = env.config.get(ConfigKeys.ENRICH, dict())
        topic_config = enrich_config.get(ConfigKeys.TOPIC, dict())
        self.topic_prefix = topic_config.get(ConfigKeys.PREFIX, '')

    def __call__(self, *args, **kwargs) -> dict:
        data = args[0]
        data['title'] = '{}{}'.format(self.topic_prefix, data.get(ConfigKeys.VERB, ''))
        return data
