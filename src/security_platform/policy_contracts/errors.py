import re


class PolicyContractError(ValueError):
    def __init__(self, code):
        self.code = code if isinstance(code, str) and re.fullmatch(r"[a-z][a-z0-9_]{0,79}", code) else "invalid_contract"
        super().__init__(self.code)
