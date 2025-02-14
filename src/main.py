import logging
logging.basicConfig(level=logging.INFO)

from meeting_bot import MeetingBot
import zoom_meeting_sdk as zoom # type: ignore

from dotenv import load_dotenv # type: ignore
import signal
import os
import gi # type: ignore

gi.require_version('GLib', '2.0')
from gi.repository import GLib # type: ignore

from transcription import handle_audio_transcription

logger = logging.getLogger(__name__)

class ZoomBotRunner:
	def __init__(self):
		self.bot = None
		self.main_loop = None
		self.shutdown_requested = False
		self.init_bot()

	def init_bot(self):
		self.bot = MeetingBot()
		try:
			self.bot.init()
		except Exception as e:
			logger.exception(f"Error initializing bot, error: {e}")
			self.exit_process()

		self.bot.set_callbacks(
			on_audio_transcription_needed_callback=handle_audio_transcription
		)

	def exit_process(self):
		"""Clean shutdown of the bot and main loop"""
		logger.info("Starting cleanup process...")
		
		# Set flag to prevent re-entry
		if self.shutdown_requested:
			return False
		self.shutdown_requested = True
		
		try:
			if self.bot:
				if self.bot.get_meeting_status() != zoom.MEETING_STATUS_ENDED:
					self.bot.leave_meeting()
				logger.info("Cleaning up bot...")
				self.bot.cleanup()
				
			self.force_exit()
					
		except Exception as e:
			logger.exception(f"Error during cleanup, error: {e}")
			self.force_exit()
	
		return False

	def force_exit(self):
		logger.info("Forcing exit...")
		os._exit(0)

	def on_signal(self, signum, frame):
		"""Signal handler for SIGINT and SIGTERM"""
		logger.info(f"Received signal {signum}")
		if self.main_loop:
			GLib.timeout_add(100, self.exit_process)
		else:
			self.exit_process()

	def on_timeout(self):
		"""Regular timeout callback"""
		meeting_status = self.bot.get_meeting_status()
		if meeting_status == zoom.MEETING_STATUS_ENDED:
			logger.info("Meeting ended detected, cleaning up...")
			if self.main_loop:
				GLib.timeout_add(100, self.exit_process)
			else:
				self.exit_process()
			return False
		
		if self.shutdown_requested:
			return False
		return True

	def run(self):
		self.main_loop = GLib.MainLoop()

		GLib.timeout_add(100, self.on_timeout)

		try:
			logger.info("Starting main event loop")
			self.main_loop.run()
		except KeyboardInterrupt:
			logger.info("Interrupted by user, shutting down...")
		except Exception as e:
			logger.exception(f"Error in main loop, error: {e}")
		finally:
			self.exit_process()

def main():
	load_dotenv()
	
	runner = ZoomBotRunner()
	
	signal.signal(signal.SIGINT, runner.on_signal)
	signal.signal(signal.SIGTERM, runner.on_signal)
	
	runner.run()

if __name__ == "__main__":
	main()