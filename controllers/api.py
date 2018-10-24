#from google.appengine.ext import blobstore

from controllers.base import BaseController

SIZE_LIMIT = 10 * (2 ** 20) # 10 MB


class UploadController(BaseController):

    def post(self):

        # takes a url to redirect to after upload, returns a valid blobstore upload url
        # remove `gs_bucket_name` to use the blobstore without Google Cloud Storage
        redirect_url = self.get_argument('url')
        path = self.gcs_bucket + '/' + self.user.slug
        url = '' #blobstore.create_upload_url(redirect_url, max_bytes_per_blob=SIZE_LIMIT, gs_bucket_name=path)

        self.renderJSON({'url': url})
