from enum import StrEnum, unique, auto, IntEnum


@unique
class ObjectType(StrEnum):
    PLAYLIST_VOICE = '1'
    PLAYLIST = '2'
    PRIVATE_VOICE = '3'
    SUGGESTED_VOICE = '5'
    SUGGESTED_VIDEO = '6'
    SUGGESTED_MEME = '7'
    PLAYLIST_MEMBER = '8'
    PLAYLIST_MEMBER_VOICE = '9'


class InvalidMemeTag(ValueError):
    def __str__(self):
        return 'invalid_meme_tag'


class LongMemeTag(ValueError):
    def __str__(self):
        return 'long_meme_tag'


class TooManyMemeTags(ValueError):
    def __str__(self):
        return 'too_many_meme_tags'


@unique
class ReportResult(IntEnum):
    REPORTED = auto()
    REPORTED_BEFORE = auto()
    REPORT_FAILED = auto()


@unique
class SearchType(IntEnum):
    NAMES = auto()
    TAGS = auto()
    ALL = auto()
