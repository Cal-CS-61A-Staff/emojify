import abc
from typing import List, Type


class Integration(abc.ABC):
    def __init__(self, message: str, token):
        self._message = message
        self._token = token
        self._process()

    def _process(self):
        pass

    @property
    def message(self):
        return self._message

    @property
    def attachments(self):
        return []


def combine_integrations(integrations: List[Type[Integration]]):
    class CombinedIntegration(Integration):
        def _process(self):
            text = self._message
            attachments = []
            for integration_type in integrations:
                integration = integration_type(text, self._token)
                text = integration.message
                attachments.extend(integration.attachments)
            self._text = text
            self._attachments = attachments

        @property
        def message(self):
            return self._text

        @property
        def attachments(self):
            return self._attachments

    return CombinedIntegration
