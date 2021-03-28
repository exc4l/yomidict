import fugashi
import srt
import re
import ebooklib
from collections import Counter
from tqdm import tqdm
from pathlib import Path
from zipfile import ZipFile
from ebooklib import epub


class DictMaker:
    """docstring for DictMaker"""

    def __init__(self):
        self.tagger = fugashi.Tagger()
        if self.tagger.dictionary_info[0]["size"] < 872000:
            print("Please execute 'python -m unidic download'")
            raise ImportError
        self.wcounter = Counter()
        self.refcounter = Counter()
        self.hiragana = set(
            "あえいおうかけきこくさしすせそたちつてとなにぬねのはひふへほ"
            "まみむめもやゆよらりるれろわをんがぎぐげござじずぜぞだぢづ"
            "でどばびぶべぼぱぴぷぺぽゃょゅっぁぃぉぅぇゎゝゐゑゔ"
        )

        self.katakana = set(
            "アエイオウカケキコクサシスセソタチツテトナニヌネノハヒフヘホ"
            "マミムメモヤユヨラリルレロワヲウンガギグゲゴザジズゼゾダヂヅ"
            "デドバビブベボパピプペポょャュィョェァォッーゥヮヴヵヶﾘｫｶｯｮｼｵﾌｷﾏﾉﾀ"
        )
        self.sentence_marker = set("。、!！？」「』『（）〝〟)(\n")
        self.all_kanji_set = set(
            chr(uni) for uni in range(ord("一"), ord("龯") + 1)
        ) | set("〆々")
        self.allowed = (
            self.all_kanji_set | self.sentence_marker | self.katakana | self.hiragana
        )

    def _clean_html(self, text):
        text = re.sub(r'<font size="1">(.*?)<\/font>', "", text)
        text = re.sub(r"<rt>(.*?)<\/rt>", "", text)
        text = "".join(filter(self.allowed.__contains__, text))
        text = re.sub(r"\n+", "\n", text)
        return text

    def _clean_txt(self, text):
        text = "".join(filter(self.allowed.__contains__, text))
        text = re.sub(r"\n+", "\n", text)
        return text

    def _clean_srt(self, text):
        subs = list(srt.parse(text))

        def remove_names(text):
            return re.sub(r"\（(.*?)\）", "", text)

        text = "".join(f"{remove_names(s.content)}\n" for s in subs)
        return self._clean_txt(text)

    def _clean_epub(self, file):
        book = epub.read_epub(file)
        text = str()
        for doc in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            text += str(doc.content.decode("utf-8-sig")) + "\n"
        return self._clean_html(text)

    def normalize_refcounter(self, value):
        """Use this if you haven't normalized the Counter before due to feeding several file lists or single texts"""
        for key in self.refcounter.keys():
            self.refcounter[key] /= value

    def feed_text(self, text, refcounter_add=False):
        total_tokens = list()
        for sen in text.split("\h"):
            sen_tokens = [
                w.feature.lemma.split("-")[0] if w.feature.lemma else w.surface
                for w in self.tagger(sen)
            ]
            sen_tokens = [
                w
                for w in sen_tokens
                if not (
                    w in self.hiragana
                    or w in self.katakana
                    or w in self.sentence_marker
                )
            ]
            total_tokens.extend(sen_tokens)
        if refcounter_add:
            self.refcounter.update(set(total_tokens))
        self.wcounter.update(total_tokens)

    def feed_files(self, filelist, reset_refcounter=True, normalize_refcounter=True):
        if reset_refcounter:
            self.refcounter = Counter()
        for entry in tqdm(filelist):
            file = Path(entry)
            if file.suffix == ".html":
                with open(file, "r", encoding="utf-8") as f:
                    text = self._clean_html(f.read())
            elif file.suffix == ".txt":
                with open(file, "r", encoding="utf-8") as f:
                    text = self._clean_txt(f.read())
            elif file.suffix == ".srt":
                with open(file, "r", encoding="utf-8") as f:
                    text = self._clean_srt(f.read())
            elif file.suffix == ".epub":
                text = self._clean_epub(file)
            else:
                print(f"unable to process {entry} due to it being {file.suffix}")
                raise FileNotFoundError
            self.feed_text(text, refcounter_add=True)
        # normalize refcounter
        if normalize_refcounter:
            total = len(filelist)
            for key in self.refcounter.keys():
                self.refcounter[key] /= total

    def save(self, filepath, dictname, only_rank_and_freq=False):
        fpath = Path(filepath)
        if fpath.suffix != ".zip":
            fpath = fpath.parent / (fpath.name + ".zip")
        yomi_title = '{"title":"' + dictname + '_W","format":3,"revision":"frequency1"}'
        freqstr = ""
        idx = 1
        for tok in self.wcounter.most_common():
            if only_rank_and_freq:
                freqstr += f'["{tok[0]}","freq"," {idx} F: {tok[1]}"],'
            else:
                freqstr += f'["{tok[0]}","freq"," {idx} F: {tok[1]} %: {self.refcounter.get(tok[0],0)*100:.2f}"],'
            idx += 1
        freqstr = "[" + freqstr[:-1] + "]"
        with ZipFile(fpath, "w") as zipf:
            zipf.writestr("index.json", yomi_title)
            zipf.writestr("term_meta_bank_1.json", freqstr)
