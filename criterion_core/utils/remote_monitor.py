import json
import logging
import requests
import numpy as np
from tensorflow.keras.callbacks import Callback


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.number):
            return obj.item()
        return json.JSONEncoder.default(self, obj)


class RemoteMonitor(Callback):
    """Callback used to stream events to a server.

    Requires the `requests` library.
    Events are sent to `root + '/publish/epoch/end/'` by default. Calls are
    HTTP POST, with a `data` argument which is a
    JSON-encoded dictionary of event data.
    If send_as_json is set to True, the content type of the request will be
    application/json. Otherwise the serialized JSON will be sent within a form.

    Arguments:
        root: String; root url of the target server.
        path: String; path relative to `root` to which the events will be sent.
        field: String; JSON field under which the data will be stored.
            The field is used only if the payload is sent within a form
            (i.e. send_as_json is set to False).
        headers: Dictionary; optional custom HTTP headers.
        send_as_json: Boolean; whether the request should be
            sent as application/json.
    """

    def __init__(self,
                 root='http://localhost:9000',
                 path='/publish/epoch/end/',
                 field='data',
                 headers=None,
                 send_as_json=False):
        super(RemoteMonitor, self).__init__()

        self.root = root
        self.path = path
        self.field = field
        self.headers = headers
        self.send_as_json = send_as_json

    def on_epoch_end(self, epoch, logs=None):
        if requests is None:
            raise ImportError('RemoteMonitor requires the `requests` library.')
        logs = logs or {}
        send = {}
        send['epoch'] = epoch
        for k, v in logs.items():
            send[k] = v
        try:
            if self.send_as_json:
                requests.post(self.root + self.path, json=send, headers=self.headers)
            else:
                requests.post(
                    self.root + self.path, {self.field: json.dumps(send, cls=NumpyEncoder)},
                    headers=self.headers)
        except requests.exceptions.RequestException:
            logging.warning('Warning: could not reach RemoteMonitor '
                            'root server at ' + str(self.root))