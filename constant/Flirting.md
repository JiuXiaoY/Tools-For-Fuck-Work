# This is a chat

My English is not very good! So, when I wrote this text, there might have been many mistakes. But for me, this is indeed
a real and life-like situation.
This is not exactly a good day, but I still need to come to work. I want to write something, during my breaks from work,
to record my absurd yet unchangeable life.
I'm just an ordinary person. Even though most people believe that after going to university, one will become a bit
better than the average person and that going to university can lead to a lot of money, the reality is that I haven't
done very well. In this era where good wine needs a good cellar to be discovered, the nourishment I absorbed seems not
to have enabled me to grow into a taller tree.
I don't know what kind of changes I should make, or perhaps I am already one of those who needs to change, or maybe I
just want to be an ordinary person. To achieve something significant, one must undergo transformation. This goes against
my original intention, but what I am currently doing seems to have a bit of flaw even in its ordinariness.
It takes a long time to form a thick layer of ice; it doesn't happen overnight!
That which moves me to pity is not for me to possess!

# This is a chat
I, I, I, I—I don’t know where I come from, where I’m going, or what it all means!

# This is a chat
.. / .-- .- -. - / - --- / --. --- / .... --- -- .

# This ia an issue

需求流程：
定义一个列范围（非连续），
对于数据行来说，在 列范围 内，数据填可不填，但不在 列范围 内的，该列一定不填

数据源是具备 分组 格式的，每组是一个父体和多个子体，有些数据在组内是一致的，你如何知道分组呢？
我这定义了数据格式，比如假设有 300 行数据的话，我会给这样的形式
```json
{
  "group_1": "1 & 99",
  "group_2": "100 & 199",
  "group_3": "200 & 300"
}
```
1 & 99  ->  1 表示该组父体所在行，即该组起始行 99 则是结束行，即最后一个子体 !如果 待填模板的数据起始行是 7，则需要统一后移

数据填写规则：
每组的数据我都是分开给你的，格式如下
```json
{
  "group_1" : {
      "{列号}": "{数据}",
      "{列号}": "{数据}",
      "{列号}": "{数据}"
  },
    "group_2" : {
      "{列号}": "{数据}",
      "{列号}": "{数据}",
      "{列号}": "{数据}"
  }
}
```

有这么几种情况，
数据数 = 该组数据行数 -> 按顺序 填写
数据数 = 该组数据行数 - 1 -> 只填 子体
数据数 = 0 -> 该组该列数据不填
数据数 < 小于指定阈值 -> 该组该列循环填写数据

试用期主要负责德国站服装品类运营。上架方面，从初期逐步提升至目前每日稳定上架 100+ 产品，完成产品信息整理、关键词等基础维护，并搭建并持续完善服装品类关键词库。销售方面，月销售额呈逐月增长趋势。日常运营方面，每日检查账号健康，按计划处理买家邮件和售后，按时完成主管安排，账号保持稳定。不足是对广告投放和部分新品类经验不足。
入职以来工作顺利，主管也给了很多指导。结合德国站服装品类运营，某些反面意识不足，可以对德国站合规政策和特殊时间节点多提醒、多同步。