import os
import uuid
import re
import base64

def get_image_base64(path):
    with open(path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()

def process_base64_images(html_content, client_id, project_id):
    if not html_content:
        return html_content
    
    pattern = re.compile(r'src="data:image/([^;]+);base64,([^"]+)"')
    
    def replacer(match):
        ext = match.group(1)
        b64_data = match.group(2)
        
        asset_dir = f"data/projects/{client_id}/{project_id}/assets"
        os.makedirs(asset_dir, exist_ok=True)
        
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(asset_dir, filename)
        
        try:
            with open(filepath, "wb") as fh:
                fh.write(base64.b64decode(b64_data))
            # Store a stable, portable reference instead of an absolute
            # file:// path. Absolute file:// URIs are resolvable by
            # WeasyPrint (server-side, direct filesystem access) when
            # generating the PDF report, but are blocked by browsers when
            # the same HTML is rendered inside the Jodit editor iframe -
            # that's why images showed up fine in the report but appeared
            # broken only in the editor. We resolve this reference
            # differently depending on where the HTML is rendered (see
            # resolve_asset_images_for_editor / _for_report below).
            return f'src="asset://{client_id}/{project_id}/{filename}"'
        except Exception as e:
            return match.group(0)
            
    return pattern.sub(replacer, html_content)


def resolve_asset_images_for_editor(html_content):
    """
    Convert stored asset://<client_id>/<project_id>/<filename> references back
    into inline base64 data URIs so the Jodit editor (which renders HTML in
    the browser) can display them. Browsers block file:// resources loaded
    from an http(s) page, which is why images appeared broken only in the
    editor while working fine in the generated PDF report.
    """
    if not html_content:
        return html_content

    pattern = re.compile(r'src="asset://([^/"]+)/([^/"]+)/([^"]+)"')

    def replacer(match):
        client_id, project_id, filename = match.groups()
        filepath = os.path.join("data/projects", client_id, project_id, "assets", filename)
        ext = os.path.splitext(filename)[1].lstrip(".") or "png"
        try:
            with open(filepath, "rb") as fh:
                b64_data = base64.b64encode(fh.read()).decode()
            return f'src="data:image/{ext};base64,{b64_data}"'
        except Exception:
            return match.group(0)

    return pattern.sub(replacer, html_content)


def resolve_asset_images_for_report(html_content):
    """
    Convert stored asset://<client_id>/<project_id>/<filename> references into
    absolute file:// paths for WeasyPrint, which renders server-side and can
    read the filesystem directly.
    """
    if not html_content:
        return html_content

    pattern = re.compile(r'src="asset://([^/"]+)/([^/"]+)/([^"]+)"')

    def replacer(match):
        client_id, project_id, filename = match.groups()
        filepath = os.path.join("data/projects", client_id, project_id, "assets", filename)
        abs_path = os.path.abspath(filepath)
        return f'src="file://{abs_path}"'

    return pattern.sub(replacer, html_content)
