# Change: Flexible face enrollment (1-3 images, auto-replace)

## Why

录入强制 3 张不够灵活。同一 faceType 重新录入应覆盖旧记录。

## What

- faces 允许 1~3 张
- 同 (employeeId, faceType) 自动删旧换新
