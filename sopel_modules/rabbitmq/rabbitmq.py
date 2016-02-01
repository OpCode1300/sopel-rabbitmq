# coding=utf-8


from __future__ import unicode_literals, absolute_import, division, print_function

import json
import logging
import os
import urlparse

import pika
from sopel import module
from sopel.config.types import StaticSection, ValidatedAttribute

# reduce log level
# logging.getLogger("pika").setLevel(logging.WARNING)

# or, disable propagation
logging.getLogger("pika").propagate = False


class rabbitmqSection(StaticSection):
    username = ValidatedAttribute('username')
    """API username"""

    password = ValidatedAttribute('password')
    """API password"""

    host = ValidatedAttribute('host')
    """API host address"""


def configure(config):
    config.define_section('rabbitmq', rabbitmqSection)
    config.rabbitmq.configure_setting(
        'username', 'username for rabbitmq API')
    config.rabbitmq.configure_setting(
        'password', 'API password')
    config.rabbitmq.configure_setting(
        'host', 'hostname or IP of Rabbit server')


def setup(bot):
    bot.config.define_section('rabbitmq', rabbitmqSection)


@module.interval(30)
def process_queue(bot):
    # Parse CLODUAMQP_URL (fallback to localhost)
    username = bot.config.rabbitmq.username
    password = bot.config.rabbitmq.password
    host = bot.config.rabbitmq.host

    url = "amqp://" + username + ":" + password + "@" + host
    params = pika.URLParameters(url)
    params.socket_timeout = 5
    connection = pika.BlockingConnection(params)  # Connect to CloudAMQP
    channel = connection.channel()

    while True:
        method_frame, header_frame, body = channel.basic_get('hello')
        if method_frame:
            msg = json.loads(body)
            bot.msg(msg['channel'], msg['body'])
            channel.basic_ack(method_frame.delivery_tag)
        else:
            # bot.msg("#cfme-bot-test", 'No more messages returned')
            break
    connection.close()
