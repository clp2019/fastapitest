import os
import cloudinary
import cloudinary.uploader
try:
    from app.core.config import settings
except ImportError:
    settings = None

def get_cloudinary_config():
    if settings:
        cloud_name = getattr(settings, "CLOUDINARY_CLOUD_NAME", None)
        api_key = getattr(settings, "CLOUDINARY_API_KEY", None)
        api_secret = getattr(settings, "CLOUDINARY_API_SECRET", None)
    else:
        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        api_key = os.getenv("CLOUDINARY_API_KEY")
        api_secret = os.getenv("CLOUDINARY_API_SECRET")
    print(f"Cloudinary config: cloud_name={cloud_name}, api_key={api_key}, api_secret={'set' if api_secret else 'missing'}")
    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True,
    )

get_cloudinary_config()


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
