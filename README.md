# yomidict
create dictionaries for yomichan

MWE:
```python
import yomidict
dm = yomidict.DictMaker()
filelist = ["test.html" for _ in range(5)]
dm.feed_files(filelist)
dm.save("zipfile.zip", "name_in_yomichan")
```