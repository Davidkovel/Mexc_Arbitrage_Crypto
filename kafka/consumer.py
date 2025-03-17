import asyncio
import json
from typing import Dict, Any

from confluent_kafka import Consumer, KafkaError

from aiogram_bot.bot import TelegramBot
from utils.logger import logger


class ArbitrageConsumer:
    def __init__(self, bootstrap_servers: str, topic: str, group_id: str, telegram_bot: TelegramBot):
        """
        Initialize the Kafka consumer for arbitrage notifications

        Args:
            bootstrap_servers: Comma-separated list of broker addresses
            topic: Kafka topic to consume messages from
            group_id: Consumer group ID
            telegram_bot: Instance of TelegramBot for sending messages
        """
        self.topic = topic
        self.telegram_bot = telegram_bot
        self.consumer_config = {
            'bootstrap.servers': bootstrap_servers,
            'group.id': group_id,
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': True,
            'max.poll.interval.ms': 300000,  # 5 minutes
            'session.timeout.ms': 30000,  # 30 seconds
        }
        self.consumer = Consumer(self.consumer_config)
        self.consumer.subscribe([topic])
        logger.info(f"Subscribed to topic: {topic}")
        self.running = False

    async def start(self):
        """Start the consumer process"""
        self.running = True
        await self._consume_messages()

    async def stop(self):
        """Stop the consumer process"""
        self.running = False
        self.consumer.close()
        logger.info("Kafka consumer stopped")

    async def _consume_messages(self):
        """Main consumption loop"""
        logger.info(f"Starting to consume messages from topic: {self.topic}")

        try:
            while self.running:
                msg = self.consumer.poll(timeout=1.0)

                if msg is None:
                    await asyncio.sleep(0.1)  # Short sleep to prevent CPU hogging
                    continue

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        # End of partition, not an error
                        continue
                    else:
                        logger.error(f"Consumer error: {msg.error()}")
                        continue

                try:
                    # Decode and parse the message
                    value = json.loads(msg.value().decode('utf-8'))
                    key = msg.key().decode('utf-8') if msg.key() else None

                    # Process the message and send to Telegram
                    logger.info(f"Received arbitrage notification for {key}")
                    await self._process_arbitrage_notification(value)

                except json.JSONDecodeError:
                    logger.error(f"Failed to parse message: {msg.value()}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Fatal error in Kafka consumer: {e}", exc_info=True)
        finally:
            if self.consumer:
                self.consumer.close()
                logger.info("Kafka consumer closed")

    async def _process_arbitrage_notification(self, message: Dict[str, Any]):
        """
        Process an arbitrage notification and send it to Telegram

        Args:
            message: The message dictionary from Kafka
        """
        try:
            # Extract data from the message
            formatted_message = message.get('formatted_message')
            thread_id = message.get('thread_id')
            dex_url = message.get('urls', {}).get('dex')
            mexc_url = message.get('urls', {}).get('mexc')

            # Send to Telegram using your existing bot
            logger.info(f"Sending notification to Telegram thread {thread_id}")
            await self.telegram_bot.send_message(
                text=formatted_message,
                message_thread_id=thread_id,
                dex_url=dex_url,
                mexc_url=mexc_url
            )
            logger.info(f"Successfully sent notification to thread {thread_id}")

        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}", exc_info=True)

