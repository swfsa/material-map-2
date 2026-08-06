// 中国关键物资进口结构 Mock 数据 — 桑基图
export const sankeyData = {
  nodes: [
    // 来源国
    { name: '澳大利亚', depth: 0 },
    { name: '巴西', depth: 0 },
    { name: '俄罗斯', depth: 0 },
    { name: '沙特', depth: 0 },
    { name: '美国', depth: 0 },
    { name: '印尼', depth: 0 },
    { name: '智利', depth: 0 },
    { name: '马来西亚', depth: 0 },
    // 品类
    { name: '铁矿石', depth: 1 },
    { name: '原油', depth: 1 },
    { name: '大豆', depth: 1 },
    { name: '天然气', depth: 1 },
    { name: '铜矿石', depth: 1 },
    { name: '煤炭', depth: 1 },
    { name: '棕榈油', depth: 1 },
    // 用途
    { name: '钢铁冶炼', depth: 2 },
    { name: '能源化工', depth: 2 },
    { name: '食品加工', depth: 2 },
    { name: '电力供应', depth: 2 },
    { name: '电子制造', depth: 2 },
    { name: '交通运输', depth: 2 },
  ],
  links: [
    // 澳大利亚 → 铁矿石、煤炭
    { source: '澳大利亚', target: '铁矿石', value: 680 },
    { source: '澳大利亚', target: '煤炭', value: 120 },
    // 巴西 → 铁矿石、大豆
    { source: '巴西', target: '铁矿石', value: 240 },
    { source: '巴西', target: '大豆', value: 180 },
    // 俄罗斯 → 原油、天然气、煤炭
    { source: '俄罗斯', target: '原油', value: 180 },
    { source: '俄罗斯', target: '天然气', value: 100 },
    { source: '俄罗斯', target: '煤炭', value: 80 },
    // 沙特 → 原油
    { source: '沙特', target: '原油', value: 260 },
    // 美国 → 大豆、天然气
    { source: '美国', target: '大豆', value: 90 },
    { source: '美国', target: '天然气', value: 60 },
    // 印尼 → 煤炭、棕榈油
    { source: '印尼', target: '煤炭', value: 140 },
    { source: '印尼', target: '棕榈油', value: 50 },
    // 智利 → 铜矿石
    { source: '智利', target: '铜矿石', value: 110 },
    // 马来西亚 → 棕榈油
    { source: '马来西亚', target: '棕榈油', value: 70 },
    // 品类 → 用途
    { source: '铁矿石', target: '钢铁冶炼', value: 910 },
    { source: '铁矿石', target: '交通运输', value: 10 },
    { source: '原油', target: '能源化工', value: 320 },
    { source: '原油', target: '交通运输', value: 120 },
    { source: '大豆', target: '食品加工', value: 220 },
    { source: '大豆', target: '能源化工', value: 50 },
    { source: '天然气', target: '能源化工', value: 80 },
    { source: '天然气', target: '电力供应', value: 60 },
    { source: '天然气', target: '食品加工', value: 20 },
    { source: '铜矿石', target: '电子制造', value: 80 },
    { source: '铜矿石', target: '交通运输', value: 20 },
    { source: '铜矿石', target: '钢铁冶炼', value: 10 },
    { source: '煤炭', target: '电力供应', value: 220 },
    { source: '煤炭', target: '钢铁冶炼', value: 100 },
    { source: '煤炭', target: '能源化工', value: 20 },
    { source: '棕榈油', target: '食品加工', value: 100 },
    { source: '棕榈油', target: '能源化工', value: 20 },
  ],
}
