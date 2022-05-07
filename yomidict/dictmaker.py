import srt
import re
import ebooklib
from collections import Counter
from tqdm import tqdm
from pathlib import Path
from zipfile import ZipFile
from ebooklib import epub
import ass
from ass_tag_parser import parse_ass, AssText
from sudachipy import Dictionary, SplitMode


class DictMaker:
    """docstring for DictMaker"""

    def __init__(self):
        self.tagger = Dictionary(dict="full").create(mode=SplitMode.A)
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
        self.numbers = set("0123456789０１２３４５６７８９")
        self.allowed = (
            self.all_kanji_set
            | self.sentence_marker
            | self.katakana
            | self.hiragana
            | self.numbers
        )

    def _check_allowed_char(self, w):
        if (
            w in self.hiragana
            or w in self.katakana
            or w in self.sentence_marker
            or w in self.numbers
            or w.isnumeric()
        ):
            return False
        return True

    def _clean_html(self, text):
        text = re.sub(r'<font size="1">(.*?)<\/font>', "", text)
        text = re.sub(r"<rt>(.*?)<\/rt>", "", text)
        text = text.replace("</p>", "\n")
        text = text.replace("</span>", "\n")
        text = text.replace("<br", "\n")
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
        text = ""
        for doc in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            text += str(doc.content.decode("utf-8-sig")) + "\n"
        return self._clean_html(text)

    def _clean_ass(self, file):
        doc = ass.parse(file)
        lines_with_tags = [event.text for event in doc.events]

        def rem_tags(line):
            try:
                return "".join(
                    i.text for i in parse_ass(line) if type(i) == AssText
                ).replace(r"\N", " ")
            except:
                return ""

        lines = [rem_tags(l) for l in lines_with_tags]
        return self._clean_txt("\n".join(lines))

    def normalize_refcounter(self, value):
        """Use this if you haven't normalized the Counter before due to feeding several file lists or single texts"""
        for key in self.refcounter.keys():
            self.refcounter[key] /= value

    def feed_text(self, text, refcounter_add=False):
        total_tokens = list()
        for sen in text.split("\n"):
            sen_tokens = [w.normalized_form() for w in self.tagger.tokenize(sen)]
            sen_tokens = [w for w in sen_tokens if self._check_allowed_char(w)]
            total_tokens.extend(sen_tokens)
        if refcounter_add:
            self.refcounter.update(set(total_tokens))
        self.wcounter.update(total_tokens)

    def feed_files(
        self,
        filelist,
        skip_errors=True,
        reset_refcounter=True,
        normalize_refcounter=True,
    ):
        if reset_refcounter:
            self.refcounter = Counter()
        failed_files = 0
        for entry in tqdm(filelist):
            file = Path(entry)
            try:
                if file.suffix == ".ass":
                    with open(file, "r", encoding="utf-8-sig") as f:
                        text = self._clean_ass(f)
                elif file.suffix == ".html":
                    with open(file, "r", encoding="utf-8-sig") as f:
                        text = self._clean_html(f.read())
                elif file.suffix == ".txt":
                    with open(file, "r", encoding="utf-8-sig") as f:
                        text = self._clean_txt(f.read())
                elif file.suffix == ".srt":
                    with open(file, "r", encoding="utf-8-sig") as f:
                        text = self._clean_srt(f.read())
                elif file.suffix == ".epub":
                    text = self._clean_epub(file)
                else:
                    print(
                        f"\nUnable to process {entry} due to being a {file.suffix} file"
                    )
                    if skip_errors:
                        failed_files += 1
                        continue
                    raise TypeError(f"{file.suffix} parser not implemented")
                self.feed_text(text, refcounter_add=True)
            except Exception as e:
                print(f"\nFailed to process {entry}: {e}")
                failed_files += 1
                if not skip_errors:
                    raise e
        # normalize refcounter
        if skip_errors:
            print(f"Skipped files: {failed_files}")
        if normalize_refcounter:
            total = len(filelist) - failed_files
            for key in self.refcounter.keys():
                self.refcounter[key] /= total

    def save(
        self,
        filepath,
        dictname,
        only_rank_and_freq=False,
        use_suffix=True,
        use_suffix_rank=True,
        use_suffix_freq=True,
    ):
        def suffix_numbers(number):
            if number > 1e6 - 1:
                return f"{int(number/1e6)}M"
            if number > 1e3 - 1:
                return f"{int(number/1e3)}K"
            return f"{number}"

        def get_num(num, use_suffix):
            if use_suffix:
                return suffix_numbers(num)
            return num

        if use_suffix:
            use_suffix_rank = True
            use_suffix_freq = True
        fpath = Path(filepath)
        if fpath.suffix != ".zip":
            fpath = fpath.parent / (fpath.name + ".zip")
        yomi_title = '{"title":"' + dictname + '","format":3,"revision":"frequency1"}'
        freqlist = list()
        idx = 1
        for tok in self.wcounter.most_common():
            if only_rank_and_freq:
                freqlist.append(
                    f'["{tok[0]}","freq","W: {get_num(idx,use_suffix_rank)} F: {get_num(tok[1], use_suffix_freq)}"],'
                )
            else:
                freqlist.append(
                    f'["{tok[0]}","freq","W: {get_num(idx,use_suffix_rank)} F: {get_num(tok[1], use_suffix_freq)} %: {self.refcounter.get(tok[0],0)*100:.2f}"],'
                )
            idx += 1
        freqstr = "".join(freqlist)
        freqstr = "[" + freqstr[:-1] + "]"
        with ZipFile(fpath, "w") as zipf:
            zipf.writestr("index.json", yomi_title)
            zipf.writestr("term_meta_bank_1.json", freqstr)
