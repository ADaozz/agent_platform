package org.example.backend.api.constant;

import lombok.Getter;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** API Token 可授出能力目录（Token asset 与开放接口 HTTP 方法一一对应） */
public final class ApiTokenGrantCatalog {

    private ApiTokenGrantCatalog() {
    }

    @Getter
    public static final class Entry {
        private final String groupKey;
        private final String groupName;
        private final String grantValue;
        private final String label;

        Entry(String groupKey, String groupName, String grantValue, String label) {
            this.groupKey = groupKey;
            this.groupName = groupName;
            this.grantValue = grantValue;
            this.label = label;
        }
    }

    private static final List<Entry> ENTRIES = Collections.unmodifiableList(Arrays.asList(
            new Entry("vm", "虚拟机", ApiTokenAssets.VM_LIST, "查询 GET /asset/vm"),
            new Entry("vm", "虚拟机", ApiTokenAssets.VM_ADD, "新增 POST /asset/vm"),
            new Entry("vm", "虚拟机", ApiTokenAssets.VM_EDIT, "修改 PUT /asset/vm"),
            new Entry("vm", "虚拟机", ApiTokenAssets.VM_DELETE, "删除 DELETE /asset/vm"),
            new Entry("app", "应用服务", ApiTokenAssets.APP_LIST, "查询 GET /asset/app"),
            new Entry("app", "应用服务", ApiTokenAssets.APP_ADD, "新增 POST /asset/app"),
            new Entry("app", "应用服务", ApiTokenAssets.APP_EDIT, "修改 PUT /asset/app"),
            new Entry("app", "应用服务", ApiTokenAssets.APP_DELETE, "删除 DELETE /asset/app")
    ));

    public static List<Entry> allEntries() {
        return ENTRIES;
    }

    /** 按 groupKey 分组，保持插入顺序 */
    public static Map<String, List<Entry>> groupedEntries() {
        Map<String, List<Entry>> grouped = new LinkedHashMap<>();
        for (Entry entry : ENTRIES) {
            grouped.computeIfAbsent(entry.getGroupKey(), key -> new ArrayList<>()).add(entry);
        }
        return grouped;
    }
}
