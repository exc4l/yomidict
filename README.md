# yomidict
Create frequency dictionaries for yomichan out of media.\
Currently supported formats are: epub, html, srt, txt

```python
pip install yomidict
```


MWE:
```python
import yomidict
dm = yomidict.DictMaker()
filelist = ["test.html"]*5 + ["test.epub"]*2 + ["test.srt"]*2
dm.feed_files(filelist)
dm.save("zipfile.zip", "name_in_yomichan")
```