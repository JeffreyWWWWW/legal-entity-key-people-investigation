import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import { spawnSync } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";


const RENDERER_VERSION = "1.0.0";
const SHEET_NAMES = [
  "01-任务概览",
  "02-主体关系",
  "03-核心人员",
  "04-证据记录",
  "05-查询与缺口",
];
const COLORS = {
  charcoal: "#263238",
  teal: "#0F766E",
  tealLight: "#DDF3F0",
  border: "#D9E1E5",
  body: "#FFFFFF",
  muted: "#F5F7F8",
  verified: "#DDF3E4",
  review: "#FFF1C7",
  blocked: "#FADBD8",
  text: "#243238",
};


function parseArgs(argv) {
  if (argv.length !== 2 && argv.length !== 4) {
    throw new Error("用法：node render_review_workbook.mjs STATE OUTPUT [--preview-dir DIR]");
  }
  const [statePath, outputPath, flag, previewDir] = argv;
  if (argv.length === 4 && flag !== "--preview-dir") {
    throw new Error(`未知参数：${flag}`);
  }
  return { statePath: path.resolve(statePath), outputPath: path.resolve(outputPath), previewDir };
}


function sortValue(value) {
  if (Array.isArray(value)) return value.map(sortValue);
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(
      Object.keys(value).sort().map((key) => [key, sortValue(value[key])]),
    );
  }
  return value;
}


function stateHash(state) {
  const facts = structuredClone(state);
  delete facts["渲染元数据"];
  const canonical = JSON.stringify(sortValue(facts));
  return crypto.createHash("sha256").update(canonical, "utf8").digest("hex").toUpperCase();
}


function byId(key) {
  return (left, right) => {
    const leftNumber = Number(String(left[key]).split("-").at(-1));
    const rightNumber = Number(String(right[key]).split("-").at(-1));
    return leftNumber - rightNumber;
  };
}


function join(values) {
  return Array.isArray(values) ? values.join("；") : (values ?? "");
}


function localWallClockDate(isoDateTime) {
  const match = isoDateTime.match(
    /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})/,
  );
  if (!match) return isoDateTime;
  const [, year, month, day, hour, minute, second] = match.map(Number);
  return new Date(Date.UTC(year, month - 1, day, hour, minute, second));
}


function buildIndexes(state) {
  const index = (records, key) => new Map(records.map((record) => [record[key], record]));
  return {
    entities: index(state["公司主体"], "主体编号"),
    relationships: index(state["主体关系"], "关系编号"),
    people: index(state["核心人员"], "人员编号"),
    positions: index(state["人员身份"], "身份编号"),
    evidence: index(state["证据记录"], "证据编号"),
    queries: index(state["查询记录"], "查询编号"),
  };
}


export function buildOverviewRows(state, hash) {
  const judgment = state["阶段判断"];
  const entities = new Map(
    state["公司主体"].map((entity) => [entity["主体编号"], entity]),
  );
  return [
    ["状态内容哈希", hash],
    ["规范版本", state["规范版本"]],
    ["Skill 版本", state["skill_version"]],
    ["任务编号", state["任务元数据"]["任务编号"]],
    ["调查基准日", state["任务元数据"]["调查基准日"]],
    [
      "输入材料",
      state["输入材料"]
        .map((source) => `${source["材料编号"]} ${source["原始名称"]}`)
        .join("；"),
    ],
    [
      "原始主体线索",
      state["目标主体引用"]
        .flatMap((entityId) => entities.get(entityId)["原始名称"])
        .join("；"),
    ],
    [
      "规范目标主体",
      state["目标主体引用"]
        .map((entityId) => `${entityId} ${entities.get(entityId)["规范法律名称"]}`)
        .join("；"),
    ],
    ["技术主题", state["技术主题"]["主题名称"]],
    ["主题描述", state["技术主题"]["主题描述"]],
    ["整体状态", judgment["整体状态"]],
    ["主体总数", judgment["主体总数"]],
    ["已识别人员数", judgment["已识别人员数"]],
    ["已核验身份数", judgment["已核验身份数"]],
    ["未解决关键事项", join(judgment["未解决关键事项"])],
    ["需要用户确认", judgment["需要用户确认"] ? "是" : "否"],
    ["用户可执行动作", join(judgment["用户可执行动作"])],
    ["渲染器版本", RENDERER_VERSION],
  ];
}


export function buildEntityRows(state, indexes) {
  const entityRows = [...state["公司主体"]].sort(byId("主体编号")).map((entity) => [
    "主体",
    entity["主体编号"],
    entity["规范法律名称"],
    entity["是否目标主体"] ? "目标主体" : "扩展主体",
    entity["注册地"],
    entity["主体身份状态"],
    join(entity["名称变体"]),
    join(entity["证据引用"]),
    join(entity["待复核事项"]),
  ]);
  const relationshipRows = [...state["主体关系"]].sort(byId("关系编号")).map((relationship) => [
    "主体关系",
    relationship["关系编号"],
    `${relationship["起点主体引用"]} ${indexes.entities.get(relationship["起点主体引用"])["规范法律名称"]}`,
    `${relationship["终点主体引用"]} ${indexes.entities.get(relationship["终点主体引用"])["规范法律名称"]}`,
    relationship["关系类型"],
    relationship["核验状态"],
    `第${relationship["扩展层数"]}跳 / ${relationship["目标业务相关性"]}`,
    join(relationship["证据引用"]),
    relationship["纳入理由"],
  ]);
  return [...entityRows, ...relationshipRows];
}


export function buildPeopleRows(state, indexes) {
  return [...state["人员身份"]].sort(byId("身份编号")).map((position) => {
    const person = indexes.people.get(position["人员引用"]);
    const entity = indexes.entities.get(position["所属主体引用"]);
    return [
      person["人员编号"],
      position["身份编号"],
      person["规范姓名"],
      entity["主体编号"],
      entity["规范法律名称"],
      position["主体层级"],
      position["身份类型"],
      position["职务原文"],
      position["身份时态"],
      position["开始日期"] ?? "",
      position["结束日期"] ?? "",
      position["时效状态"],
      position["目标业务相关性"],
      position["核验状态"],
      position["可靠性"],
      join(position["证据引用"]),
      position["纳入理由"],
      position["复核建议"],
    ];
  });
}


export function buildEvidenceRows(state) {
  return [...state["证据记录"]].sort(byId("证据编号")).map((evidence) => [
    evidence["证据编号"],
    evidence["来源类型"],
    evidence["标题"],
    evidence["URL或文件路径"],
    evidence["文件日期"] ?? "",
    evidence["查询日期"],
    evidence["证据等级"],
    evidence["核验状态"],
    join(evidence["证明范围"]),
    join(evidence["主体引用"]),
    join(evidence["主体关系引用"]),
    join(evidence["人员身份引用"]),
    evidence["关键原文"],
    evidence["持续有效说明"],
  ]);
}


export function buildQueryAndIssueRows(state) {
  const queryRows = [...state["查询记录"]].sort(byId("查询编号")).map((query) => [
    "查询",
    query["查询编号"],
    query["查询对象类型"],
    query["查询对象引用"],
    query["数据源"],
    query["查询维度"],
    query["是否独立核验"] ? "是" : "否",
    join(query["查询词"]),
    localWallClockDate(query["查询时间"]),
    query["访问结果"],
    query["命中情况"],
    join(query["命中证据引用"]),
    query["阻塞原因"],
    query["后续动作"],
  ]);
  const issueRows = [...state["冲突与待确认项"]].sort(byId("事项编号")).map((issue) => [
    "缺口",
    issue["事项编号"],
    issue["类型"],
    join(issue["关联对象引用"]),
    "",
    "",
    "",
    "",
    "",
    issue["是否关键"] ? "关键" : "非关键",
    issue["状态"],
    "",
    issue["说明"],
    issue["解决说明"],
  ]);
  return [...queryRows, ...issueRows];
}


function columnName(number) {
  let result = "";
  while (number > 0) {
    number -= 1;
    result = String.fromCharCode(65 + (number % 26)) + result;
    number = Math.floor(number / 26);
  }
  return result;
}


function applyTitle(sheet, title, width) {
  const lastColumn = columnName(width);
  sheet.mergeCells(`A1:${lastColumn}1`);
  sheet.getRange("A1").values = [[title]];
  sheet.getRange(`A1:${lastColumn}1`).format = {
    fill: COLORS.charcoal,
    font: { bold: true, color: "#FFFFFF", size: 16, name: "Microsoft YaHei" },
    verticalAlignment: "center",
  };
  sheet.getRange("1:1").format.rowHeight = 30;
  sheet.showGridLines = false;
}


function applyStatusFormatting(sheet, range, statusColumn) {
  const statusRange = sheet.getRange(`${statusColumn}5:${statusColumn}${range}`);
  statusRange.conditionalFormats.add("containsText", {
    text: "已核验",
    format: { fill: COLORS.verified, font: { color: "#245C35" } },
  });
  for (const text of ["待", "部分", "时点不明"]) {
    statusRange.conditionalFormats.add("containsText", {
      text,
      format: { fill: COLORS.review, font: { color: "#72510D" } },
    });
  }
  for (const text of ["冲突", "失败", "受限", "关键"]) {
    statusRange.conditionalFormats.add("containsText", {
      text,
      format: { fill: COLORS.blocked, font: { color: "#8A2C25" } },
    });
  }
}


function writeDetailSheet(sheet, title, headers, rows, widths, tableName, statusColumn, options = {}) {
  applyTitle(sheet, title, headers.length);
  sheet.getRange("A2").values = [["按稳定编号排序；筛选器用于复核，不改变 state.json。"]];
  sheet.getRange(`A2:${columnName(headers.length)}2`).format = {
    fill: COLORS.muted,
    font: { color: "#54646B", italic: true, name: "Microsoft YaHei" },
  };
  sheet.getRange(`A4:${columnName(headers.length)}4`).values = [headers];
  sheet.getRange(`A4:${columnName(headers.length)}4`).format = {
    fill: COLORS.teal,
    font: { bold: true, color: "#FFFFFF", name: "Microsoft YaHei" },
    verticalAlignment: "center",
    wrapText: true,
  };
  const dataRows = rows.length > 0 ? rows : [headers.map(() => "")];
  const lastRow = 4 + dataRows.length;
  sheet.getRange(`A5:${columnName(headers.length)}${lastRow}`).values = dataRows;
  sheet.getRange(`A5:${columnName(headers.length)}${lastRow}`).format = {
    fill: COLORS.body,
    font: { color: COLORS.text, name: "Microsoft YaHei", size: 10 },
    verticalAlignment: "top",
    wrapText: true,
    borders: { insideHorizontal: { style: "thin", color: COLORS.border } },
  };
  widths.forEach((width, index) => {
    sheet.getRange(`${columnName(index + 1)}:${columnName(index + 1)}`).format.columnWidth = width;
  });
  sheet.getRange("4:4").format.rowHeight = 28;
  sheet.getRange(`5:${lastRow}`).format.rowHeight = options.rowHeight ?? 42;
  const table = sheet.tables.add(`A4:${columnName(headers.length)}${lastRow}`, true, tableName);
  table.style = "TableStyleMedium2";
  table.showFilterButton = true;
  if (statusColumn) applyStatusFormatting(sheet, lastRow, statusColumn);
  if (options.dateTimeColumn) {
    sheet.getRange(`${options.dateTimeColumn}5:${options.dateTimeColumn}${lastRow}`).format.numberFormat =
      "yyyy-mm-dd hh:mm:ss";
  }
  sheet.freezePanes.freezeRows(4);
}


function writeOverview(sheet, rows) {
  applyTitle(sheet, "法律主体核心人员调查 - 任务概览", 6);
  const lastRow = rows.length + 1;
  sheet.getRange(`A2:B${lastRow}`).values = rows;
  sheet.getRange(`A2:A${lastRow}`).format = {
    fill: COLORS.tealLight,
    font: { bold: true, color: COLORS.text, name: "Microsoft YaHei" },
    verticalAlignment: "top",
  };
  sheet.getRange(`B2:B${lastRow}`).format = {
    fill: COLORS.body,
    font: { color: COLORS.text, name: "Microsoft YaHei" },
    verticalAlignment: "top",
    wrapText: true,
  };
  sheet.getRange(`A2:B${lastRow}`).format.borders = {
    insideHorizontal: { style: "thin", color: COLORS.border },
  };
  sheet.getRange("A:A").format.columnWidth = 22;
  sheet.getRange("B:B").format.columnWidth = 72;
  sheet.getRange(`2:${lastRow}`).format.rowHeight = 32;
  rows.forEach(([label, value], index) => {
    if (label !== "原始主体线索" && label !== "规范目标主体") return;
    const wrappedLines = Math.max(1, Math.ceil(String(value ?? "").length / 58));
    const rowHeight = Math.min(180, Math.max(64, wrappedLines * 16));
    sheet.getRange(`${index + 2}:${index + 2}`).format.rowHeight = rowHeight;
  });
  sheet.freezePanes.freezeRows(1);
}


async function loadArtifactTool(nodeModules) {
  const packageJson = path.join(nodeModules, "package.json");
  const requireFromBundle = createRequire(packageJson);
  const resolved = requireFromBundle.resolve("@oai/artifact-tool");
  return import(pathToFileURL(resolved).href);
}


async function patchFrozenPanes(outputPath, nodeModules) {
  const requireFromBundle = createRequire(path.join(nodeModules, "package.json"));
  const jszipModule = await import(pathToFileURL(requireFromBundle.resolve("jszip")).href);
  const JSZip = jszipModule.default;
  const zip = await JSZip.loadAsync(await fs.readFile(outputPath));
  const freezeRows = [1, 4, 4, 4, 4];
  for (let index = 0; index < freezeRows.length; index += 1) {
    const entry = `xl/worksheets/sheet${index + 1}.xml`;
    const file = zip.file(entry);
    if (!file) throw new Error(`工作簿缺少预期工作表 XML：${entry}`);
    const xml = await file.async("string");
    const rows = freezeRows[index];
    const pane =
      `<x:pane ySplit="${rows}" topLeftCell="A${rows + 1}" activePane="bottomLeft" state="frozen"/>`;
    if (xml.includes("<x:sheetView") && /<x:sheetView\b[^>]*\/>/.test(xml)) {
      zip.file(
        entry,
        xml.replace(/<x:sheetView\b([^>]*)\/>/, `<x:sheetView$1>${pane}</x:sheetView>`),
      );
      continue;
    }
    if (xml.includes("<x:sheetViews")) {
      zip.file(entry, xml.replace("</x:sheetView>", `${pane}</x:sheetView>`));
      continue;
    }
    const views = `<x:sheetViews><x:sheetView workbookViewId="0">${pane}</x:sheetView></x:sheetViews>`;
    const marker = "<x:sheetFormatPr";
    if (!xml.includes(marker)) throw new Error(`无法定位工作表视图插入点：${entry}`);
    zip.file(entry, xml.replace(marker, `${views}${marker}`));
  }
  await fs.writeFile(outputPath, await zip.generateAsync({ type: "nodebuffer" }));
}


function validateState(statePath) {
  const python = process.env.CODEX_PYTHON;
  if (!python) throw new Error("缺少 CODEX_PYTHON，无法运行状态校验器");
  const validator = path.join(path.dirname(fileURLToPath(import.meta.url)), "validate_state.py");
  const result = spawnSync(python, [validator, statePath], { encoding: "utf8" });
  if (result.status !== 0) {
    const detail = (result.stderr || result.stdout || "未知校验错误").trim();
    throw new Error(`状态校验未通过：${detail}`);
  }
}


async function main() {
  const args = parseArgs(process.argv.slice(2));
  const nodeModules = process.env.CODEX_NODE_MODULES;
  if (!nodeModules) throw new Error("缺少 CODEX_NODE_MODULES");
  validateState(args.statePath);
  const state = JSON.parse(await fs.readFile(args.statePath, "utf8"));
  const hash = stateHash(state);
  const indexes = buildIndexes(state);
  const { SpreadsheetFile, Workbook } = await loadArtifactTool(nodeModules);
  const workbook = Workbook.create();
  const sheets = SHEET_NAMES.map((name) => workbook.worksheets.add(name));

  writeOverview(sheets[0], buildOverviewRows(state, hash));
  writeDetailSheet(
    sheets[1],
    "主体与关系",
    ["记录类型", "编号", "起点/主体", "终点/层级", "关系/注册地", "核验状态", "扩展与相关性", "证据引用", "纳入理由/待复核事项"],
    buildEntityRows(state, indexes),
    [12, 13, 30, 30, 18, 14, 21, 18, 42],
    "EntityRelationshipTable",
    "F",
  );
  writeDetailSheet(
    sheets[2],
    "核心人员与身份",
    ["人员编号", "身份编号", "规范姓名", "主体编号", "所属主体", "主体层级", "身份类型", "职务原文", "身份时态", "开始日期", "结束日期", "时效状态", "业务相关性", "核验状态", "可靠性", "证据引用", "纳入理由", "复核建议"],
    buildPeopleRows(state, indexes),
    [13, 13, 20, 13, 30, 16, 16, 25, 13, 14, 14, 17, 15, 14, 11, 18, 36, 36],
    "PeoplePositionTable",
    "N",
  );
  writeDetailSheet(
    sheets[3],
    "证据记录",
    ["证据编号", "来源类型", "标题", "URL或文件路径", "文件日期", "查询日期", "证据等级", "核验状态", "证明范围", "主体引用", "关系引用", "身份引用", "关键原文", "持续有效说明"],
    buildEvidenceRows(state, indexes),
    [13, 20, 30, 42, 14, 14, 14, 14, 24, 18, 18, 18, 50, 36],
    "EvidenceTable",
    "H",
    { rowHeight: 64 },
  );
  writeDetailSheet(
    sheets[4],
    "查询记录与调查缺口",
    ["记录类型", "编号", "对象/事项类型", "对象引用", "数据源", "查询维度", "独立核验", "查询词", "查询时间", "访问/关键性", "命中/状态", "证据引用", "阻塞原因/说明", "后续动作/解决说明"],
    buildQueryAndIssueRows(state, indexes),
    [12, 13, 18, 18, 24, 18, 12, 30, 24, 16, 20, 18, 42, 42],
    "QueryIssueTable",
    "K",
    { dateTimeColumn: "I" },
  );

  await fs.mkdir(path.dirname(args.outputPath), { recursive: true });
  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(args.outputPath);
  await patchFrozenPanes(args.outputPath, nodeModules);
  await fs.rm(`${args.outputPath}.inspect.ndjson`, { force: true });

  if (args.previewDir) {
    const previewDir = path.resolve(args.previewDir);
    await fs.mkdir(previewDir, { recursive: true });
    for (const name of SHEET_NAMES) {
      const preview = await workbook.render({ sheetName: name, autoCrop: "all", scale: 1, format: "png" });
      await fs.writeFile(path.join(previewDir, `${name}.png`), new Uint8Array(await preview.arrayBuffer()));
    }
  }
}


if (process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url) {
  main().catch((error) => {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  });
}
