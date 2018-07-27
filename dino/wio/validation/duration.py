from dino.validation.generic import GenericValidator


class DurationValidator(object):
    durations = {
        'd': 'days',
        'h': 'hours',
        'm': 'minutes',
        's': 'seconds'
    }
    durations_help = ', '.join('%s (%s)' % (unit, human) for unit, human in durations.items())

    def __init__(self, ban_duration):
        if ban_duration is None or ban_duration == '':
            raise ValueError('empty ban duration')

        valid_ends = {'s', 'm', 'h', 'd'}
        if ban_duration[-1] not in valid_ends:
            raise ValueError('invalid ban duration: %s' % ban_duration)

        if ban_duration.startswith('-'):
            raise ValueError('can not set negative ban duration: %s' % ban_duration)

        if ban_duration.startswith('+'):
            ban_duration = ban_duration[1:]

        if not GenericValidator.is_digit(ban_duration[:-1]):
            raise ValueError('invalid ban duration, not a number: %s' % ban_duration)
