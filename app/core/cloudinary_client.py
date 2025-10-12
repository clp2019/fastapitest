import os
import cloudinary
import cloudinary.uploader

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True,
)


def upload_sync(file_stream, folder=None, public_id=None, **options):
    opts = {}
    if folder:
        opts["folder"] = folder
    if public_id:
        opts["public_id"] = public_id
    opts.update(options)
    return cloudinary.uploader.upload(file_stream, **opts)


def destroy_sync(public_id, **options):
    return cloudinary.uploader.destroy(public_id, **options)
