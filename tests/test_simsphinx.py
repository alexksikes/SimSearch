from simsearch import simsphinx

s = '(@similar 6876876--sad--asd--asd--saddas) @-genre 3423423 @-year 2009'
q = simsphinx.QuerySimilar()

q.Parse(s)

print repr(q)
print q.user
print q.sphinx
print q.uniq
