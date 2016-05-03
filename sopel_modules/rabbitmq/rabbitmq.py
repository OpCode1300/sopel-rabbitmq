# coding=utf-8


from __future__ import unicode_literals, absolute_import, division, print_function

import json
import logging
import os
import urlparse
import pika
import yaml
import gnupg

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

    rabbit_queue_name = ValidatedAttribute('rabbit_queue_name')
    """RabbitMQ queue name"""

    gpg_home = ValidatedAttribute('gpg_home')
    """GPG data directory"""

    whitelist_path = ValidatedAttribute('whitelist_path')
    """GPG whitelist path"""


def configure(config):
    config.define_section('rabbitmq', rabbitmqSection)

    config.rabbitmq.configure_setting(
        'username', 'Username for RabbitMQ API')

    config.rabbitmq.configure_setting(
        'password', 'API password')

    config.rabbitmq.configure_setting(
        'host', 'Hostname or IP of Rabbit server')

    config.rabbitmq.configure_setting(
        'rabbit_queue_name', 'RabbitMQ queue name to monitor')

    config.rabbitmq.configure_setting(
        'gpg_home', 'GPG data directory')

    config.rabbitmq.configure_setting(
        'whitelist_path', 'GPG whitelist file path')


def setup(bot):
    bot.config.define_section('rabbitmq', rabbitmqSection)


@module.interval(30)
def process_queue(bot):
    # RabbitMQ
    username = bot.config.rabbitmq.username
    password = bot.config.rabbitmq.password
    host = bot.config.rabbitmq.host
    rabbit_queue_name = bot.config.rabbitmq.rabbit_queue_name

    # gpg
    gpg_home = bot.config.rabbitmq.gpg_home
    gpg = gnupg.GPG(gnupghome=gpg_home)
    whitelist_path = bot.config.rabbitmq.whitelist_path

    # Load whitelist
    whitelist = []
    with open(whitelist_path, 'r') as ymlfile:
        for key in yaml.safe_load(ymlfile)['allowed_keys']:
            whitelist.append(key.replace(' ', ''))

    url = "amqp://" + username + ":" + password + "@" + host
    params = pika.URLParameters(url)
    params.socket_timeout = 5
    connection = pika.BlockingConnection(params)  # Connect to CloudAMQP
    channel = connection.channel()

    try:
        while True:
            method, properties, body = channel.basic_get(rabbit_queue_name)
            if method:
                if properties:
                    header_channel = properties.headers.get('channel', None)
                    header_gpg = properties.headers.get('gpg', None)
                    if header_channel in bot.channels:
                        if header_gpg:
                            verified = gpg.verify(body)
                            message = body.split('-----BEGIN PGP SIGNATURE-----')[0].split('\n\n')[1].rstrip('\n')
                            if (verified.trust_level is not None and verified.trust_level >= verified.TRUST_FULLY) \
                                and (verified.fingerprint is not None and verified.fingerprint in whitelist):
                                    bot.msg(header_channel, message)
                                    channel.basic_ack(method.delivery_tag)
                            else:  # verified.trust_level
                                print('Message did not pass verification.')
                        else:  # header_gpg
                            break
                    else:  # header_channel
                        print("Bot not in channel: " + str(header_channel))
                else:  # properties
                    break

            else:  # method
                break
    finally:
        connection.close()
