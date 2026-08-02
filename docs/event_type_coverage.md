# Event type coverage

Generated from ingested bronze data spanning 2015-01-01 00:00:00 to 2015-02-20 23:59:59.

| type | first seen | last seen | event count |
|---|---|---|---|
| PushEvent | 2015-01-01 00:00:00 | 2015-02-20 23:59:59 | 12,058,439 |
| CreateEvent | 2015-01-01 00:00:01 | 2015-02-20 23:59:57 | 2,811,867 |
| IssueCommentEvent | 2015-01-01 00:00:06 | 2015-02-20 23:59:59 | 2,299,391 |
| PullRequestReviewCommentEvent | 2015-01-01 00:00:08 | 2015-02-20 23:59:58 | 373,422 |
| PullRequestEvent | 2015-01-01 00:00:11 | 2015-02-20 23:59:58 | 1,176,179 |
| ForkEvent | 2015-01-01 00:00:16 | 2015-02-20 23:59:39 | 817,107 |
| WatchEvent | 2015-01-01 00:00:18 | 2015-02-20 23:59:58 | 2,190,751 |
| DeleteEvent | 2015-01-01 00:00:30 | 2015-02-20 23:59:57 | 455,899 |
| IssuesEvent | 2015-01-01 00:00:30 | 2015-02-20 23:59:59 | 1,195,903 |
| CommitCommentEvent | 2015-01-01 00:00:55 | 2015-02-20 23:59:58 | 162,786 |
| GollumEvent | 2015-01-01 00:01:10 | 2015-02-20 23:59:22 | 251,475 |
| ReleaseEvent | 2015-01-01 00:02:19 | 2015-02-20 23:59:43 | 75,166 |
| MemberEvent | 2015-01-01 00:04:11 | 2015-02-20 23:59:53 | 122,998 |
| PublicEvent | 2015-01-01 00:09:13 | 2015-02-20 23:59:38 | 24,775 |

A type whose first-seen date falls after the ingested range's start entered the Events API later than that point; a type whose last-seen date falls before the range's end stopped being emitted before that point. Either case means a time series spanning that type's absence would misread instrumentation change as a real trend (see README caveats and section 7.3 of the build brief).

## Known event types absent from this range

Zero events of these types appear anywhere in the ingested range above. For a type that launched after this range's end (e.g. PullRequestReviewEvent, which GitHub introduced with its 2016 formal-review UI), this is expected, not a gap -- confirm against GitHub's own type history before treating it as one:

- PullRequestReviewEvent
- PullRequestReviewThreadEvent
- SponsorshipEvent

