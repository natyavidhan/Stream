tags = [
    ["Tech", 14],
    ["Food", 7],
    ["GameDev", 4],
    ["Study", 1],
    ["Coding", 10],
    ["Social", 3],
    ["Trend", 13],
    ["Books", 19],
    ["Geek", 25],
    ["Music", 6],
    ["Dance", 1]
]
total = 0
for i, a in tags:
    total = total + a

pure = [[i, round((a/total*100)*0.5)] for i, a in tags]

print(pure)
total = 0
for i, a in pure:
    total = total + a
print(total)

    
