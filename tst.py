import AO3

url = "https://archiveofourown.org/works/45957766/chapters/117174691"
workid = AO3.utils.workid_from_url(url)
print(f"Work ID: {workid}")
work = AO3.Work(workid)

print(f"Chapters: {work.nchapters}")
for i, chapter in enumerate(work.chapters, start=1):    
    print(f"\nChapter {i}:")
    print(f"Title: {chapter.title}")
    print(f"URL: {chapter.url}")
    print(f"Words: {chapter.words}")
    print(f"Content:\n{chapter.text[:500]}...")