package org.example.backend.api.constant;

import lombok.Getter;
import org.example.backend.api.vo.OpenApiParamVO;

import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 开放接口文档元数据目录（仅 implemented=true 的条目进入文档 API） */
public final class OpenApiDocCatalog {

    private OpenApiDocCatalog() {
    }

    @Getter
    public static final class Entry {
        private final String id;
        private final String groupKey;
        private final String groupName;
        private final String grant;
        private final String requiredPermission;
        private final String method;
        private final String path;
        private final String summary;
        private final String description;
        private final List<OpenApiParamVO> queryParams;
        private final List<OpenApiParamVO> bodyParams;
        private final Map<String, Object> requestBodyExample;
        private final Map<String, Object> responseExample;
        private final boolean implemented;

        Entry(String id, String groupKey, String groupName, String grant, String requiredPermission,
              String method, String path, String summary, String description,
              List<OpenApiParamVO> queryParams, List<OpenApiParamVO> bodyParams,
              Map<String, Object> requestBodyExample, Map<String, Object> responseExample,
              boolean implemented) {
            this.id = id;
            this.groupKey = groupKey;
            this.groupName = groupName;
            this.grant = grant;
            this.requiredPermission = requiredPermission;
            this.method = method;
            this.path = path;
            this.summary = summary;
            this.description = description;
            this.queryParams = queryParams;
            this.bodyParams = bodyParams;
            this.requestBodyExample = requestBodyExample;
            this.responseExample = responseExample;
            this.implemented = implemented;
        }
    }

    private static OpenApiParamVO qp(String name, String type, boolean required, String description, String example) {
        OpenApiParamVO p = new OpenApiParamVO();
        p.setName(name);
        p.setType(type);
        p.setRequired(required);
        p.setDescription(description);
        p.setExample(example);
        return p;
    }

    private static OpenApiParamVO bp(String name, String type, boolean required, String description, String example) {
        return qp(name, type, required, description, example);
    }

    private static final List<OpenApiParamVO> VM_QUERY_PARAMS = Collections.unmodifiableList(Arrays.asList(
            qp("hostId", "string", false, "虚机 UUID，传则查单条", null),
            qp("hostName", "string", false, "虚机名称，模糊匹配", null),
            qp("vmIp", "string", false, "虚机 IP，模糊匹配", null),
            qp("lifecycleStatus", "string", false, "生命周期：creating/running/stopped/pending_delete/destroyed", null),
            qp("ownerUserId", "long", false, "按 owner 用户 ID 筛选", null),
            qp("networkZone", "string", false, "网段：idc / cfdc", null),
            qp("env", "string", false, "环境：prod / dev / test", null),
            qp("pageNum", "int", false, "页码，默认 1", "1"),
            qp("pageSize", "int", false, "每页条数，默认 10，最大 50", "10")
    ));

    private static final List<OpenApiParamVO> VM_BODY_PARAMS = Collections.unmodifiableList(Arrays.asList(
            bp("hostId", "string", true, "虚机 ID", "a1000001-0000-4000-8000-000000000001"),
            bp("hostName", "string", true, "虚机名称", "web-prod-01"),
            bp("osType", "string", true, "操作系统类型", "CentOS"),
            bp("osVersion", "string", false, "操作系统版本", "7.9"),
            bp("vmIp", "string", false, "虚机 IP", "10.10.1.101"),
            bp("cpuCores", "int", false, "CPU 核数", "4"),
            bp("memoryGb", "int", false, "内存 GB", "8"),
            bp("diskGb", "int", false, "磁盘 GB", "100"),
            bp("physicalHostIp", "string", false, "宿主机 IP", "192.168.1.10"),
            bp("lifecycleStatus", "string", false, "生命周期状态（仅允许按顺序推进）", "running"),
            bp("networkZone", "string", true, "网段：idc / cfdc", "idc"),
            bp("env", "string", true, "环境：prod / dev / test", "prod"),
            bp("remark", "string", false, "备注", null)
    ));

    private static final Map<String, Object> VM_PUT_BODY_EXAMPLE;

    static {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("hostId", "a1000001-0000-4000-8000-000000000001");
        body.put("hostName", "web-prod-01");
        body.put("osType", "CentOS");
        body.put("osVersion", "7.9");
        body.put("vmIp", "10.10.1.101");
        body.put("cpuCores", 4);
        body.put("memoryGb", 8);
        body.put("diskGb", 100);
        body.put("physicalHostIp", "192.168.1.10");
        body.put("lifecycleStatus", "running");
        body.put("networkZone", "idc");
        body.put("env", "prod");
        body.put("remark", null);
        VM_PUT_BODY_EXAMPLE = Collections.unmodifiableMap(body);
    }

    private static final Map<String, Object> VM_LIST_RESPONSE_EXAMPLE;

    static {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("hostId", "a1000001-0000-4000-8000-000000000001");
        row.put("hostName", "web-prod-01");
        row.put("osType", "CentOS");
        row.put("osVersion", "7.9");
        row.put("vmIp", "10.10.1.101");
        row.put("cpuCores", 4);
        row.put("memoryGb", 8);
        row.put("diskGb", 100);
        row.put("physicalHostIp", "192.168.1.10");
        row.put("lifecycleStatus", "running");
        Map<String, Object> owner = new LinkedHashMap<>();
        owner.put("id", 1001);
        owner.put("label", "admin");
        row.put("owner", owner);
        row.put("networkZone", "idc");
        row.put("env", "prod");
        row.put("remark", null);
        row.put("createTime", "2026-08-21 15:59:24");
        row.put("updateTime", "2026-08-21 15:59:24");

        Map<String, Object> data = new LinkedHashMap<>();
        data.put("total", 1);
        data.put("rows", Collections.singletonList(row));

        Map<String, Object> resp = new LinkedHashMap<>();
        resp.put("code", 0);
        resp.put("msg", "成功");
        resp.put("data", data);
        VM_LIST_RESPONSE_EXAMPLE = Collections.unmodifiableMap(resp);
    }

    private static final Map<String, Object> VM_PUT_RESPONSE_EXAMPLE;

    static {
        Map<String, Object> resp = new LinkedHashMap<>();
        resp.put("code", 0);
        resp.put("msg", "更新成功");
        resp.put("data", null);
        VM_PUT_RESPONSE_EXAMPLE = Collections.unmodifiableMap(resp);
    }

    private static final List<OpenApiParamVO> APP_QUERY_PARAMS = Collections.unmodifiableList(Arrays.asList(
            qp("appId", "string", false, "应用 UUID，传则查单条", null),
            qp("appName", "string", false, "应用名称，模糊匹配", null),
            qp("hostId", "string", false, "所属虚机 ID", null),
            qp("vmIp", "string", false, "虚机 IP，模糊匹配", null),
            qp("appStatus", "string", false, "应用状态：running / stopped", null),
            qp("pageNum", "int", false, "页码，默认 1", "1"),
            qp("pageSize", "int", false, "每页条数，默认 10，最大 50", "10")
    ));

    private static final List<OpenApiParamVO> APP_BODY_PARAMS = Collections.unmodifiableList(Arrays.asList(
            bp("appId", "string", true, "应用 ID", "b2000001-0000-4000-8000-000000000001"),
            bp("appName", "string", true, "应用名称", "order-service"),
            bp("deployPath", "string", true, "部署路径", "/opt/apps/order"),
            bp("appStatus", "string", true, "应用状态：running / stopped", "running")
    ));

    private static final Map<String, Object> APP_PUT_BODY_EXAMPLE;

    static {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("appId", "b2000001-0000-4000-8000-000000000001");
        body.put("appName", "order-service");
        body.put("deployPath", "/opt/apps/order");
        body.put("appStatus", "running");
        APP_PUT_BODY_EXAMPLE = Collections.unmodifiableMap(body);
    }

    private static final Map<String, Object> APP_LIST_RESPONSE_EXAMPLE;

    static {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("appId", "b2000001-0000-4000-8000-000000000001");
        row.put("appName", "order-service");
        row.put("hostId", "a1000001-0000-4000-8000-000000000001");
        row.put("hostName", "web-prod-01");
        row.put("vmIp", "10.10.1.101");
        row.put("deployPath", "/opt/apps/order");
        row.put("appStatus", "running");
        row.put("createTime", "2026-08-21 15:59:24");
        row.put("updateTime", "2026-08-21 15:59:24");

        Map<String, Object> data = new LinkedHashMap<>();
        data.put("total", 1);
        data.put("rows", Collections.singletonList(row));

        Map<String, Object> resp = new LinkedHashMap<>();
        resp.put("code", 0);
        resp.put("msg", "成功");
        resp.put("data", data);
        APP_LIST_RESPONSE_EXAMPLE = Collections.unmodifiableMap(resp);
    }

    private static final Map<String, Object> APP_PUT_RESPONSE_EXAMPLE = VM_PUT_RESPONSE_EXAMPLE;

    private static final List<Entry> ENTRIES = Collections.unmodifiableList(Arrays.asList(
            new Entry(
                    "vm-list", "vm", "虚拟机",
                    ApiTokenAssets.VM_LIST, "asset:vm:list",
                    "GET", "/asset/vm",
                    "查询虚机列表",
                    "分页查询虚机资产；传 hostId 时返回单条详情。外部调用须 Token 授权 vm:list（或旧值 vm）。",
                    VM_QUERY_PARAMS, Collections.emptyList(),
                    null, VM_LIST_RESPONSE_EXAMPLE, true
            ),
            new Entry(
                    "vm-edit", "vm", "虚拟机",
                    ApiTokenAssets.VM_EDIT, "asset:vm:edit",
                    "PUT", "/asset/vm",
                    "修改虚机",
                    "更新虚机信息；仅 owner 可修改。外部调用须 Token 授权 vm:edit。",
                    Collections.emptyList(), VM_BODY_PARAMS,
                    VM_PUT_BODY_EXAMPLE, VM_PUT_RESPONSE_EXAMPLE, true
            ),
            new Entry(
                    "app-list", "app", "应用服务",
                    ApiTokenAssets.APP_LIST, "asset:app:list",
                    "GET", "/asset/app",
                    "查询应用列表",
                    "分页查询应用资产；传 appId 时返回单条详情。外部调用须 Token 授权 app:list（或旧值 app）。",
                    APP_QUERY_PARAMS, Collections.emptyList(),
                    null, APP_LIST_RESPONSE_EXAMPLE, true
            ),
            new Entry(
                    "app-edit", "app", "应用服务",
                    ApiTokenAssets.APP_EDIT, "asset:app:edit",
                    "PUT", "/asset/app",
                    "修改应用",
                    "更新应用信息；仅所属虚机 owner 可修改。外部调用须 Token 授权 app:edit。",
                    Collections.emptyList(), APP_BODY_PARAMS,
                    APP_PUT_BODY_EXAMPLE, APP_PUT_RESPONSE_EXAMPLE, true
            )
    ));

    public static List<Entry> allEntries() {
        return ENTRIES;
    }

    public static List<Entry> implementedEntries() {
        List<Entry> result = new java.util.ArrayList<>();
        for (Entry entry : ENTRIES) {
            if (entry.isImplemented()) {
                result.add(entry);
            }
        }
        return result;
    }
}
