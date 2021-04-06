# yomidict
Create frequency dictionaries for yomichan out of media.\
Currently supported formats are: epub, html, srt, ass, txt


![](https://github.com/exc4l/yomidict/blob/main/example.png)

```python
pip install yomidict
```


MWE:
```python
import yomidict
dm = yomidict.DictMaker()
filelist = ["test.html"]*5 + ["test.epub"]*2 + ["test.srt"]*2
dm.feed_files(filelist)
dm.save("zipfile.zip", "name_in_yomichan", use_suffix=True)
```

# Docs:

## DictMaker Object
### wcounter
Is a Counter which saves the number of occurences for the tokens that were found during feeding.

### refcounter
Keeps track of in how many files a certain token was found. E.g. a value of 0.5 (if normalized) would mean that the token occurs in 50% of all files that were fed.

## DictMaker.feedfiles()
```python
def feed_files(
        self,
        filelist,
        skip_errors=True,
        reset_refcounter=True,
        normalize_refcounter=True,
    )
```
skip_erros: does exactly as the name suggests, it skips errors. During processing of a bunch of files all sorts of errors could occur which would abort the feeding. This might be undesirable and so they can be skipped. The errored files will also be taken in consideration when calculating the DictMaker.refcounter.

reset_refcounter: resets the refcounter before feeding files.

normalize_refcounter: count/total_number_of_files. Therefore, if a token comes up in 8 out of 10 books the value of the counter would be 0.8 instead of 8. This makes it easier to read even without knowing the total number of files that were fed into DictMaker.

## DictMaker.save()
```python
def save(
        self,
        filepath,
        dictname,
        only_rank_and_freq=False,
        use_suffix=True,
        use_suffix_rank=False,
        use_suffix_freq=False,
    )
```
only_rank_and_freq: by default it the word rank, the word frequency and the refcounter_value get saved. This deactivates the refcounter_value.

use_suffix: activates use_suffix_rank and use_suffix_freq.

use_suffix_rank: if the number is above 1000 the number gets replaced by "num/1000 K" e.g. 2530 becomes 2K and 2434455 becomes 2M.

use_suffix_freq: same as use_suffix_freq but for the frequency

## DictMaker.feed_text()
```python
def feed_text(self, text, refcounter_add=False)
```
can be used to feed a string into DictMaker.

refcounter_add: If true it adds 1 occurrence in refcounter to all the tokens that were found in the fed text.

### How to feed a large text file

Do you want to use refcounter? If yes, do you know the number of works inside the large text file? No? Don't use refcounter.

If you do know the number of works inside the large text file, do you know where one work ends and the other begins? Nice, just read it as chunks and let it add to the refcounter and normalize it in the end. If not, don't use refcounter.

To feed a large text file you can just read the text file line by line or sentence by sentence and utilizie the `DictMaker._clean_txt()` function.

```python
dm = yomidict.DictMaker()
for line in large_txt_file:
    dm.feed_text(dm._clean_txt(line))
```

If you know the boundaries of each work and can it eat in chunks you could something like this:

```python
dm = yomidict.DictMaker()
for work in large_txt_file:
    dm.feed_text(dm._clean_txt(work), refcounter_add=True)
dm.normalize_refcounter(works_in_large_txt_file)
```
