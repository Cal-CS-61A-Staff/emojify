import abc
from typing import List, Type


class Integration(abc.ABC):
    def __init__(self, message: str, token):
        self.message = message
        self.token = token
        self.process()

    def process(self):
        pass

    @property
    def text(self):
        return self.message

    @property
    def attachments(self):
        return []


def combine_integrations(integrations: List[Type[Integration]]):
    class CombinedIntegration(Integration):
        def process(self):
            text = self.message
            attachments = []
            for integration_type in integrations:
                integration = integration_type(text, self.token)
                text = integration.text
                attachments.extend(integration.attachments)
            self._text = text
            self._attachments = attachments

        @property
        def text(self):
            return self._text

        @property
        def attachments(self):
            return self._attachments

    return CombinedIntegration
