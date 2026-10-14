from enum import IntEnum


class ExitCode(IntEnum):
    OK = 0
    UNEXPECTED = 1
    INVALID_INPUT = 2
    CONNECTION_FAILURE = 3
    UNSUPPORTED_QUERY = 4
    TIMEOUT = 5
    INDEX_APPLY_FAILURE = 6


class IndexOptimizerError(Exception):
    exit_code: ExitCode = ExitCode.UNEXPECTED


class ConfigError(IndexOptimizerError):
    exit_code = ExitCode.INVALID_INPUT


class NotImplementedYetError(IndexOptimizerError):
    exit_code = ExitCode.UNEXPECTED


class ConnectionFailedError(IndexOptimizerError):
    exit_code = ExitCode.CONNECTION_FAILURE
