import pickle
import os
import sys
from enum import Enum
from .. import config

class Status(Enum):
    """ Enum containing all statuses Ricecooker can have

        Steps:
            INIT: Ricecooker process has been started
            CONSTRUCT_CHANNEL: Ricecooker is ready to call sushi chef's construct_channel method
            CREATE_TREE: Ricecooker is ready to create relationships between nodes
            DOWNLOAD_FILES: Ricecooker is ready to start downloading files
            GET_FILE_DIFF: Ricecooker is ready to get file diff from Kolibri Studio
            START_UPLOAD: Ricecooker is ready to start uploading files to Kolibri Studio
            UPLOADING_FILES: Ricecooker is in the middle of uploading files
            UPLOAD_CHANNEL: Ricecooker is ready to upload the channel to Kolibri Studio
            PUBLISH_CHANNEL: Ricecooker is ready to publish the channel to Kolibri
            DONE: Ricecooker is done
            LAST: Place where Ricecooker left off
    """
    INIT = 0
    CONSTRUCT_CHANNEL = 1
    CREATE_TREE = 2
    DOWNLOAD_FILES = 3
    COMPRESS_FILES = 4
    GET_FILE_DIFF = 5
    START_UPLOAD = 6
    UPLOADING_FILES = 7
    UPLOAD_CHANNEL = 8
    PUBLISH_CHANNEL = 9
    DONE = 10
    LAST = 11


class RestoreManager:
    """ Manager for handling resuming rice cooking process

        Attributes:
            restore_path (str): path to .pickle file to store progress
            channel (Channel): channel Ricecooker is creating
            tree (ChannelManager): manager Ricecooker is using
            files_downloaded ([str]): list of files that have been downloaded
            file_mapping ({filename:...}): filenames mapped to metadata
            files_failed ([str]): list of files that failed to download
            file_diff ([str]): list of files that don't exist on Kolibri Studio
            files_uploaded ([str]): list of files that have been successfully uploaded
            channel_link (str): link to uploaded channel
            channel_id (str): id of channel that has been uploaded
            status (str): status of Ricecooker
    """

    def __init__(self):
        self.channel = None
        self.tree = None
        self.files_downloaded = []
        self.file_mapping = {}
        self.files_failed = []
        self.file_diff = []
        self.files_uploaded = []
        self.channel_link = None
        self.channel_id = None
        self.status = Status.INIT

    def check_for_session(self, status=None):
        """ check_for_session: see if session is in progress
            Args:
                status (str): step to check if last session reached (optional)
            Returns: boolean indicating if session exists
        """
        status = Status.LAST if status is None else status
        return os.path.isfile(self.get_restore_path(status)) and os.path.getsize(self.get_restore_path(status)) > 0

    def get_restore_path(self, status=None):
        """ get_restore_path: get path to restoration file
            Args:
                status (str): step to get restore file (optional)
            Returns: string path to restoration file
        """
        status = self.get_status() if status is None else status
        return config.get_restore_path(status.name.lower())

    def record_progress(self):
        """ record_progress: save progress to respective restoration file
            Args: None
            Returns: None
        """
        with open(self.get_restore_path(Status.LAST), 'wb') as handle, open(self.get_restore_path(), 'wb') as step_handle:
            pickle.dump(self, handle)
            pickle.dump(self, step_handle)

    def load_progress(self, resume_step):
        """ load_progress: loads progress from restoration file
            Args: resume_step (str): step at which to resume session
            Returns: manager with progress from step
        """
        resume_step = Status[resume_step]
        progress_path = self.get_restore_path(resume_step)

        # If progress is corrupted, revert to step before
        while not self.check_for_session(resume_step):
            sys.stderr.write("\nRicecooker has not reached {0} status. Reverting to earlier step...".format(resume_step.name))
            # All files are corrupted or absent, restart process
            if resume_step.value - 1 < 0:
                self.init_session()
                return self
            resume_step = Status(resume_step.value - 1)
            progress_path = self.get_restore_path(resume_step)
        sys.stderr.write("\nStarting from status {0}".format(resume_step.name))

        # Load manager
        with open(progress_path, 'rb') as handle:
            manager = pickle.load(handle)
            if isinstance(manager, RestoreManager):
                return manager
            else:
                return self

    def get_status(self):
        """ get_status: retrieves current status of Ricecooker
            Args: None
            Returns: string status of Ricecooker
        """
        return self.status

    def get_status_val(self):
        """ get_status_val: retrieves value of status of Ricecooker
            Args: None
            Returns: number value of status of Ricecooker
        """
        return self.status.value

    def init_session(self):
        """ init_session: sets session to beginning status
            Args: None
            Returns: None
        """
        # Clear out previous session's restoration files
        for status in Status:
            path = self.get_restore_path(status)
            if os.path.isfile(path):
                os.remove(path)

        self.record_progress()
        self.status = Status.CONSTRUCT_CHANNEL # Set status to next step
        self.record_progress()

    def set_channel(self, channel):
        """ set_channel: records progress from constructed channel
            Args: channel (Channel): channel Ricecooker is creating
            Returns: None
        """
        self.status = Status.CREATE_TREE # Set status to next step
        self.channel = channel
        self.record_progress()

    def set_tree(self, tree):
        """ set_channel: records progress from creating the tree
            Args: tree (ChannelManager): manager Ricecooker is using
            Returns: None
        """
        self.status = Status.DOWNLOAD_FILES # Set status to next step
        self.tree = tree
        self.record_progress()

    def set_files(self, files_downloaded, file_mapping, files_failed):
        """ set_files: records progress from downloading files
            Args:
                files_downloaded ([str]): list of files that have been downloaded
                file_mapping ({filename:...}): filenames mapped to metadata
                files_failed ([str]): list of files that failed to download
            Returns: None
        """
        self.status = Status.COMPRESS_FILES # Set status to next step
        self.files_downloaded = files_downloaded
        self.file_mapping = file_mapping
        self.files_failed = files_failed
        self.record_progress()

    def set_compressed_files(self, files_downloaded, file_mapping, files_failed):
        """ set_compressed_files: records progress from compressing files
            Args:
                files_downloaded ([str]): list of files that have been downloaded
                file_mapping ({filename:...}): filenames mapped to metadata
                files_failed ([str]): list of files that failed to download
            Returns: None
        """
        self.status = Status.GET_FILE_DIFF # Set status to next step
        self.files_downloaded = files_downloaded
        self.file_mapping = file_mapping
        self.files_failed = files_failed
        self.record_progress()

    def set_diff(self, file_diff):
        """ set_diff: records progress from getting file diff
            Args: file_diff ([str]): list of files that don't exist on Kolibri Studio
            Returns: None
        """
        self.status = Status.START_UPLOAD # Set status to next step
        self.file_diff = file_diff
        self.record_progress()

    def set_uploading(self, files_uploaded):
        """ set_uploading: records progress during uploading files
            Args: files_uploaded ([str]): list of files that have been successfully uploaded
            Returns: None
        """
        self.status = Status.UPLOADING_FILES
        self.files_uploaded = files_uploaded
        self.record_progress()

    def set_uploaded(self, files_uploaded):
        """ set_uploaded: records progress after uploading files
            Args: files_uploaded ([str]): list of files that have been successfully uploaded
            Returns: None
        """
        self.files_uploaded = files_uploaded
        self.status = Status.UPLOAD_CHANNEL # Set status to next step
        self.record_progress()

    def set_channel_created(self, channel_link, channel_id):
        """ set_channel_created: records progress after creating channel on Kolibri Studio
            Args:
                channel_link (str): link to uploaded channel
                channel_id (str): id of channel that has been uploaded
            Returns: None
        """
        self.status = Status.PUBLISH_CHANNEL
        self.channel_link = channel_link
        self.channel_id = channel_id
        self.record_progress()

    def set_published(self):
        """ set_published: records progress after channel has been published
            Args: None
            Returns: None
        """
        self.status = Status.DONE
        self.record_progress()

    def set_done(self):
        """ set_done: records progress after Ricecooker process has been completed
            Args: None
            Returns: None
        """
        self.status = Status.DONE
        self.record_progress()

        # Delete restoration point for last step to indicate process has been completed
        os.remove(self.get_restore_path(Status.LAST))