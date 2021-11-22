import os
import yaml

config_path = os.environ['DINO_CONFIG']
gn_environment = os.environ['DINO_ENV']


class ConfigDict:
    class DefaultValue:
        def __init__(self):
            pass

        def lower(self):
            raise NotImplementedError()

        def format(self):
            raise NotImplementedError()

    def __init__(self, params=None, override=None):
        self.params = params or dict()
        self.override = override

    def subp(self, parent):
        p = dict(parent.params)
        p.update(self.params)
        if self.override is not None:
            p.update(self.override)
        return ConfigDict(p, self.override)

    def sub(self, **params):
        p = dict(self.params)
        p.update(params)
        if self.override is not None:
            p.update(self.override)
        return ConfigDict(p, self.override)

    def set(self, key, val, domain: str=None):
        if domain is None:
            self.params[key] = val
        else:
            if domain not in self.params:
                self.params[domain] = dict()
            self.params[domain][key] = val

    def keys(self):
        return self.params.keys()

    def get(self, key, default: Union[None, object]=DefaultValue, params=None, domain=None):
        def config_format(s, _params):
            if s is None:
                return s

            if isinstance(s, list):
                return [config_format(r, _params) for r in s]

            if isinstance(s, dict):
                kw = dict()
                for k, v in s.items():
                    kw[k] = config_format(v, _params)
                return kw

            if not isinstance(s, str):
                return s

            if s.lower() == 'null' or s.lower() == 'none':
                return ''

            try:
                import re
                keydb = set('{' + key + '}')

                while True:
                    sres = re.search("{.*?}", s)
                    if sres is None:
                        break

                    # avoid using the same reference twice
                    if sres.group() in keydb:
                        raise RuntimeError(
                                "found circular dependency in config value '{0}' using reference '{1}'".format(
                                        s, sres.group()))
                    keydb.add(sres.group())
                    s = s.format(**_params)

                return s
            except KeyError as e:
                raise RuntimeError("missing configuration key: " + str(e))

        if params is None:
            params = self.params

        if domain is not None:
            if domain in self.params:
                # domain keys are allowed to be empty, e.g. for default amqp exchange etc.
                value = self.params.get(domain).get(key)
                if value is None:
                    if default is None:
                        return ''
                    return default

                return config_format(value, params)

        if key in self.params:
            return config_format(self.params.get(key), params)

        if default == ConfigDict.DefaultValue:
            raise KeyError(key)

        return config_format(default, params)

    def __contains__(self, key):
        if key in self.params:
            return True
        return False

    def __iter__(self):
        for k in sorted(self.params.keys()):
            yield k

    def __len__(self, *args, **kwargs):
        return len(self.params)


def find_config(config_path: str) -> dict:
    default_path = "dino.yaml"

    path = os.path.join(config_path, default_path)

    if not os.path.isfile(path):
        raise RuntimeError('no such path: {}'.format(path))

    try:
        config_dict = yaml.safe_load(open(path))
    except Exception as e:
        raise RuntimeError("Failed to open configuration {0}: {1}".format(path, str(e)))

    return config_dict


def load_secrets_file(config_dict: dict) -> dict:
    from string import Template
    import ast

    secrets_path = 'secrets/%s.yaml' % gn_environment

    # first substitute environment variables, which holds precedence over the yaml config (if it exists)
    template = Template(str(config_dict))
    template = template.safe_substitute(os.environ)

    if os.path.isfile(secrets_path):
        try:
            secrets = yaml.safe_load(open(secrets_path))
        except Exception as e:
            raise RuntimeError("Failed to open secrets configuration {0}: {1}".format(secrets_path, str(e)))
        template = Template(template)
        template = template.safe_substitute(secrets)

    return ast.literal_eval(template)


def create_conf():
    config_dict = find_config(config_path)

    if gn_environment not in config_dict:
        raise RuntimeError('no configuration found for environment "%s"' % gn_environment)

    config_dict = config_dict[gn_environment]
    config_dict = load_secrets_file(config_dict)

    return config_dict


conf = create_conf()
