# Event type coverage

Generated from ingested bronze data spanning 2015-01-01 00:00:00 to 2024-06-02 23:59:59.

| type | first seen | last seen | event count |
|---|---|---|---|
| PushEvent | 2015-01-01 00:00:00 | 2024-06-02 23:59:59 | 10,233,501 |
| CreateEvent | 2015-01-01 00:00:01 | 2024-06-02 23:59:59 | 2,368,927 |
| IssueCommentEvent | 2015-01-01 00:00:06 | 2024-06-02 23:59:59 | 1,637,846 |
| PullRequestReviewCommentEvent | 2015-01-01 00:00:08 | 2024-06-02 23:59:47 | 269,697 |
| PullRequestEvent | 2015-01-01 00:00:11 | 2024-06-02 23:59:59 | 962,884 |
| ForkEvent | 2015-01-01 00:00:16 | 2024-06-02 23:59:57 | 600,962 |
| WatchEvent | 2015-01-01 00:00:18 | 2024-06-02 23:59:59 | 1,673,137 |
| IssuesEvent | 2015-01-01 00:00:30 | 2024-06-02 23:59:59 | 860,073 |
| DeleteEvent | 2015-01-01 00:00:30 | 2024-06-02 23:59:59 | 398,872 |
| CommitCommentEvent | 2015-01-01 00:00:55 | 2024-06-02 23:59:23 | 114,713 |
| GollumEvent | 2015-01-01 00:01:10 | 2024-06-02 23:59:53 | 176,975 |
| ReleaseEvent | 2015-01-01 00:02:19 | 2024-06-02 23:59:52 | 69,888 |
| MemberEvent | 2015-01-01 00:04:11 | 2024-06-02 23:59:31 | 89,035 |
| PublicEvent | 2015-01-01 00:09:13 | 2024-06-02 23:59:54 | 27,750 |
| PullRequestReviewEvent | 2024-01-15 09:00:00 | 2024-06-02 23:59:56 | 34,524 |

A type whose first-seen date falls after the ingested range's start entered the Events API later than that point; a type whose last-seen date falls before the range's end stopped being emitted before that point. Either case means a time series spanning that type's absence would misread instrumentation change as a real trend (see README caveats and section 7.3 of the build brief).
