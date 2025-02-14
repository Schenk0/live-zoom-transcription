import logging 
import zoom_meeting_sdk as zoom # type: ignore
import os
import gi # type: ignore

import utils as utils

gi.require_version('GLib', '2.0')
from gi.repository import GLib # type: ignore

logger = logging.getLogger(__name__)

class MeetingBot:
	def __init__(self):
		self.meeting_service = None
		self.setting_service = None
		self.auth_service = None

		self.auth_event = None
		self.meeting_service_event = None

		self.reminder_controller = None

		self.my_user_id = None
		self.participants_ctrl = None
		self.meeting_reminder_event = None

		self.chat_ctrl = None
		self.chat_ctrl_event = None

		self.audio_buffer = bytearray()

		# Audio recording related attributes
		self.audio_source = None
		self.audio_helper = None
		self.audio_settings = None
		self.recording_ctrl = None
		self.audio_ctrl = None
		self.audio_ctrl_event = None
		self.audio_raw_data_sender = None
		self.virtual_audio_mic_event_passthrough = None

		self.on_audio_transcription_needed_callback = None

	def init(self):
		if os.environ.get('ZOOM_CLIENT_ID') is None:
			raise Exception('No ZOOM_CLIENT_ID found in environment. Please define this in a .env file located in the repository root')
		if os.environ.get('ZOOM_CLIENT_SECRET') is None:
			raise Exception('No ZOOM_CLIENT_SECRET found in environment. Please define this in a .env file located in the repository root')
		if os.environ.get('JOIN_URL') is None:
			raise Exception('No JOIN_URL found in environment. Please define this in a .env file located in the repository root')

		init_param = zoom.InitParam()

		init_param.strWebDomain = "https://zoom.us"
		init_param.strSupportUrl = "https://zoom.us"
		init_param.enableGenerateDump = True
		init_param.emLanguageID = zoom.SDK_LANGUAGE_ID.LANGUAGE_English
		init_param.enableLogByDefault = True

		init_sdk_result = zoom.InitSDK(init_param)
		if init_sdk_result != zoom.SDKERR_SUCCESS:
			raise Exception('InitSDK failed')
		
		self.__create_services()

	def set_callbacks(
		self,
		on_audio_transcription_needed_callback
	):
		self.on_audio_transcription_needed_callback = on_audio_transcription_needed_callback

	def __on_join(self):
		self.meeting_reminder_event = zoom.MeetingReminderEventCallbacks(onReminderNotifyCallback=self.__on_reminder_notify)
		self.reminder_controller = self.meeting_service.GetMeetingReminderController()
		self.reminder_controller.SetEvent(self.meeting_reminder_event)

		self.recording_ctrl = self.meeting_service.GetMeetingRecordingController()

		def on_recording_privilege_changed(can_rec):
			logger.info(f"Recording privilege changed. Can record: {can_rec}")
			if can_rec:
				GLib.timeout_add_seconds(1, self.__start_raw_recording)
			else:
				self.__stop_raw_recording()

		self.recording_event = zoom.MeetingRecordingCtrlEventCallbacks(
			onRecordPrivilegeChangedCallback=on_recording_privilege_changed
		)
		self.recording_ctrl.SetEvent(self.recording_event)

		GLib.timeout_add_seconds(1, self.__start_raw_recording)

	def __join_meeting(self):
		try:
			join_url = os.environ.get('JOIN_URL')
			meeting_id, password = utils.extract_meeting_details(join_url)
			
			if not meeting_id:
				raise ValueError(f"Could not extract meeting ID from URL: {join_url}")
			
			display_name = "Zoom Bot"
			meeting_number = int(meeting_id)

			join_param = zoom.JoinParam()
			join_param.userType = zoom.SDKUserType.SDK_UT_WITHOUT_LOGIN

			param = join_param.param
			param.meetingNumber = meeting_number
			param.userName = display_name
			param.psw = password if password else ""
			param.vanityID = ""
			param.customer_key = ""
			param.webinarToken = ""
			param.isVideoOff = False
			param.isAudioOff = False

			join_result = self.meeting_service.Join(join_param)
			if join_result == zoom.SDKERR_SUCCESS:
				logger.info("Successfully joined meeting")
			else:
				logger.error(f"Failed to join meeting. Error: {join_result}")
				return

			self.audio_settings = self.setting_service.GetAudioSettings()
			self.audio_settings.EnableAutoJoinAudio(True)
		except Exception as e:
			logger.exception("Error joining meeting")
			raise

	def __on_reminder_notify(self, content, handler):
		try:
			if handler:
				handler.Accept()
		except Exception as e:
			logger.exception("Error in on_reminder_notify")

	def __auth_return(self, result):
		if result == zoom.AUTHRET_SUCCESS:
			logger.info("Auth completed successfully, joining meeting...")
			return self.__join_meeting()

		raise Exception(f"Failed to authorize. result = {result}")
	
	def __meeting_status_changed(self, status, iResult):
		if status == zoom.MEETING_STATUS_INMEETING:
			self.__on_join()

		logger.info(f"New meeting status: {status}")

	def __create_services(self):
		self.meeting_service = zoom.CreateMeetingService()
		
		self.setting_service = zoom.CreateSettingService()

		self.meeting_service_event = zoom.MeetingServiceEventCallbacks(onMeetingStatusChangedCallback=self.__meeting_status_changed)
						
		meeting_service_set_revent_result = self.meeting_service.SetEvent(self.meeting_service_event)
		if meeting_service_set_revent_result != zoom.SDKERR_SUCCESS:
			raise Exception("Meeting Service set event failed")
		
		self.auth_event = zoom.AuthServiceEventCallbacks(onAuthenticationReturnCallback=self.__auth_return)

		self.auth_service = zoom.CreateAuthService()

		set_event_result = self.auth_service.SetEvent(self.auth_event)
		if set_event_result != zoom.SDKERR_SUCCESS:
			logger.error(f"Failed to set event. Error: {set_event_result}")

		# Use the auth service
		auth_context = zoom.AuthContext()
		auth_context.jwt_token = utils.generate_jwt(os.environ.get('ZOOM_CLIENT_ID'), os.environ.get('ZOOM_CLIENT_SECRET'))

		result = self.auth_service.SDKAuth(auth_context)

		if result == zoom.SDKError.SDKERR_SUCCESS:
			logger.info("Authentication successful")
		else:
			logger.error(f"Authentication failed with error: {result}")

	def cleanup(self):
		if self.meeting_service:
			zoom.DestroyMeetingService(self.meeting_service)
		if self.setting_service:
			zoom.DestroySettingService(self.setting_service)
		if self.auth_service:
			zoom.DestroyAuthService(self.auth_service)

		zoom.CleanUPSDK()

	def leave_meeting(self):
		if self.meeting_service is None:
			return
		
		try:
			logger.info("Leaving meeting...")
			status = self.meeting_service.GetMeetingStatus()
			if status == zoom.MEETING_STATUS_IDLE:
				return

			self.meeting_service.Leave(zoom.LEAVE_MEETING)
		except Exception as e:
			logger.exception("Error leaving meeting")

	def get_meeting_status(self):
		try:
			return self.meeting_service.GetMeetingStatus()
		except Exception as e:
			logger.exception("Error getting meeting status")
			return None

	def send_audio_buffer_to_whisper(self):
		if not self.audio_buffer:
			logger.info("Audio buffer is empty, skipping transcription.")
			return True

		if self.on_audio_transcription_needed_callback:
			# Create a copy of the buffer and clear the original
			audio_data = bytes(self.audio_buffer)
			self.audio_buffer = bytearray()
			
			# Call the callback with the audio data and necessary parameters
			transcription_text = self.on_audio_transcription_needed_callback(
				audio_data,
				channels=1,
				sample_width=2,
				framerate=32000
			)

			if transcription_text:
				logger.info(f"Transcription text: {transcription_text}")
				# This is where we would send the transcription text
		else:
			logger.info("No transcription callback set, clearing audio buffer")
			self.audio_buffer = bytearray()

		return True  # Keep the timer running

	def __start_raw_recording(self):
		try:
			self.recording_ctrl = self.meeting_service.GetMeetingRecordingController()

			can_start_recording_result = self.recording_ctrl.CanStartRawRecording()
			if can_start_recording_result != zoom.SDKERR_SUCCESS:
				self.recording_ctrl.RequestLocalRecordingPrivilege()
				logger.info("Requesting recording privilege.")
				return

			start_raw_recording_result = self.recording_ctrl.StartRawRecording()
			if start_raw_recording_result != zoom.SDKERR_SUCCESS:
				logger.error("Start raw recording failed.")
				return

			self.audio_helper = zoom.GetAudioRawdataHelper()
			if self.audio_helper is None:
				logger.error("audio_helper is None")
				return
			
			if self.audio_source is None:
				self.audio_source = zoom.ZoomSDKAudioRawDataDelegateCallbacks(
					onOneWayAudioRawDataReceivedCallback=self.__on_one_way_audio_raw_data_received_callback,
					collectPerformanceData=True
				)

			audio_helper_subscribe_result = self.audio_helper.subscribe(self.audio_source, False)
			logger.info(f"Audio helper subscribe result: {audio_helper_subscribe_result}")

			# transcribe every 5 seconds
			GLib.timeout_add_seconds(5, self.send_audio_buffer_to_whisper)

			return True

		except Exception as e:
			logger.exception("Error starting raw recording")
			return False

	def __stop_raw_recording(self):
		try:
			if self.recording_ctrl:
				result = self.recording_ctrl.StopRawRecording()
				if result != zoom.SDKERR_SUCCESS:
					logger.error("Error stopping raw recording")
		except Exception as e:
			logger.exception("Error stopping raw recording")

	def __on_one_way_audio_raw_data_received_callback(self, data, node_id):
		try:
			if node_id != self.my_user_id:
				buffer_copy = bytes(data.GetBuffer())

				temp_buffer = bytearray(buffer_copy)
				self.audio_buffer = bytearray(bytes(self.audio_buffer) + bytes(temp_buffer))

		except Exception as e:
			logger.exception("Error in audio data callback")