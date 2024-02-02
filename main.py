"""
Copyright 2018 YoongiKim

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

import os
import requests
import shutil
from multiprocessing import Pool
import signal
import argparse
from collect_links import CollectLinks
import imghdr


class Sites:
    GOOGLE = 1
    NAVER = 2
    GOOGLE_FULL = 3
    NAVER_FULL = 4

    @staticmethod
    def get_text(code):
        if code == Sites.GOOGLE:
            return 'google'
        elif code == Sites.NAVER:
            return 'naver'
        elif code == Sites.GOOGLE_FULL:
            return 'google'
        elif code == Sites.NAVER_FULL:
            return 'naver'

    @staticmethod
class AutoCrawler:
    def __init__(self, skip_already_exist=True, n_threads=4, do_google=True, do_naver=True, download_path='download'):
        self.skip = skip_already_exist
        self.n_threads = n_threads
        self.do_google = do_google
        self.do_naver = do_naver
        self.download_path = download_path

        os.makedirs('./{}'.format(self.download_path), exist_ok=True)

    @staticmethod
    def all_dirs(path):
        paths = []
        for dir in os.listdir(path):
            if os.path.isdir(path + '/' + dir):
                paths.append(path + '/' + dir)

        return paths

    @staticmethod
    def all_files(path):
        paths = []
        for root, dirs, files in os.walk(path):
            for file in files:
                if os.path.isfile(path + '/' + file):
                    paths.append(path + '/' + file)

        return paths

    @staticmethod
    def get_extension_from_link(link, default='jpg'):
        splits = str(link).split('.')
        if len(splits) == 0:
            return default
        ext = splits[-1].lower()
        if ext == 'jpg' or ext == 'jpeg':
            return 'jpg'
        elif ext == 'gif':
            return 'gif'
        elif ext == 'png':
            return 'png'
        else:
            return default

    @staticmethod
    def validate_image(path):
        ext = imghdr.what(path)
        if ext == 'jpeg':
            ext = 'jpg'
        return ext  # returns None if not valid

    @staticmethod
    def make_dir(dirname):
        current_path = os.getcwd()
        path = os.path.join(current_path, dirname)
        if not os.path.exists(path):
            os.makedirs(path)

    @staticmethod
    def get_keywords(keywords_file='keywords.txt'):
        # read search keywords from file
        with open(keywords_file, 'r', encoding='utf-8-sig') as f:
            text = f.read()
            lines = text.split('\n')
            lines = filter(lambda x: x != '' and x is not None, lines)
            keywords = sorted(set(lines))

        print('{} keywords found: {}'.format(len(keywords), keywords))

        # re-save sorted keywords
        with open(keywords_file, 'w+', encoding='utf-8') as f:
            for keyword in keywords:
                f.write('{}\n'.format(keyword))

        return keywords

    @staticmethod
    def save_object_to_file(object, file_path, is_base64=False):
        try:
            with open('{}'.format(file_path), 'wb') as file:
                if is_base64:
                    file.write(object)
            print('Save failed - {}'.format(e))

    def download_images(self, keyword, links, site_name, max_count=0):
        self.make_dir('{}/{}'.format(self.download_path, keyword.replace('"', '')))
        total = len(links)
        success_count = 0

        if max_count == 0:
            max_count = total

        for index, link in enumerate(links):
            if success_count >= max_count:
                break

            try:
                print('Downloading {} from {}: {} / {}'.format(keyword, site_name, success_count + 1, max_count))

                response = requests.get(link, stream=True, timeout=10)
                ext = self.get_extension_from_link(link)

                no_ext_path = '{}/{}/{}_{}'.format(self.download_path.replace('"', ''), keyword, site_name,
                                                   str(index).zfill(4))
                path = no_ext_path + '.' + ext
                with open(path, 'wb') as file:
                    shutil.copyfileobj(response.raw, file)

                success_count += 1
                del response

                ext2 = self.validate_image(path)
                if ext2 is None:
                    print('Unreadable file - {}'.format(link))
                    os.remove(path)
                    success_count -= 1
                else:
                    if ext != ext2:
                        path2 = no_ext_path + '.' + ext2
                        os.rename(path, path2)
                        print('Renamed extension {} -> {}'.format(ext, ext2))

            except KeyboardInterrupt:
                break

            except Exception as e:
                print('Download failed - ', e)
                continue

    def download_from_site(self, keyword, site_code):
        site_name = Sites.get_text(site_code)

        try:
            collect = CollectLinks()  # initialize chrome driver
        except Exception as e:
            print('Error occurred while initializing chromedriver - {}'.format(e))
            return

        try:
            print('Collecting links... {} from {}'.format(keyword, site_name))

            if site_code == Sites.GOOGLE:
                links = collect.google(keyword)
            elif site_code == Sites.NAVER:
                links = collect.naver(keyword)
            else:
                print('Invalid Site Code')
                links = []

            print('Downloading images from collected links... {} from {}'.format(keyword, site_name))
            self.download_images(keyword, links, site_name)

            print('Done {} : {}'.format(site_name, keyword))

        except Exception as e:
            print('Exception {}:{} - {}'.format(site_name, keyword, e))
            return

    def download(self, args):
        self.download_from_site(keyword=args[0], site_code=args[1])

    def init_worker(self):
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        
    def do_crawling(self):
        keywords = self.get_keywords()

        tasks = []

        for keyword in keywords:
            if self.do_google:
                tasks.append([keyword, Sites.GOOGLE])
            if self.do_naver:
                tasks.append([keyword, Sites.NAVER])

        pool = Pool(self.n_threads, initializer=self.init_worker)
        pool.map(self.download, tasks)
        pool.terminate()
        pool.join()
        print('Task ended. Pool join.')

        print('End Program')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--skip', type=str, default='true',
                        help='Skips keyword already downloaded before. This is needed when re-downloading.')
    parser.add_argument('--threads', type=int, default=4, help='Number of threads to download.')
    parser.add_argument('--google', type=str, default='true', help='Download from google.com (boolean)')
    parser.add_argument('--naver', type=str, default='true', help='Download from naver.com (boolean)')
    args = parser.parse_args()

    _skip = False if str(args.skip).lower() == 'false' else True
    _threads = args.threads
    _google = False if str(args.google).lower() == 'false' else True
    _naver = False if str(args.naver).lower() == 'false' else True

    crawler = AutoCrawler(skip_already_exist=_skip, n_threads=_threads,
                          do_google=_google, do_naver=_naver)
    crawler.do_crawling()
