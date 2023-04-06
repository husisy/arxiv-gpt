import os
import requests
from tqdm import tqdm

_MY_REQUEST_HEADERS = {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'}


def download_url_and_save(url, filename=None, directory='.', headers=None, proxies=None):
    assert os.path.exists(directory)
    response = requests.get(url, headers=headers, proxies=proxies, stream=True)
    response.raise_for_status()
    if filename is None:
        filepath = os.path.join(directory, url.rsplit('/',1)[1])
    else:
        filepath = os.path.join(directory, filename)
    if not os.path.exists(filepath):
        tmp_filepath = filepath + '.incomplete'
        tmp0 = {'total':int(response.headers['content-length']), 'unit':'iB', 'unit_scale':True}
        with open(tmp_filepath, 'wb') as fid, tqdm(**tmp0) as progress_bar:
            for x in response.iter_content(chunk_size=1024): #1kiB
                progress_bar.update(len(x))
                fid.write(x)
        os.rename(tmp_filepath, filepath)
    return filepath
