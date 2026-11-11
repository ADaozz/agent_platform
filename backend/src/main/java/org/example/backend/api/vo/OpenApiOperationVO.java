package org.example.backend.api.vo;

import lombok.Data;

import java.util.List;
import java.util.Map;

@Data
public class OpenApiOperationVO {

    private String id;

    private String groupKey;

    private String groupName;

    private String grant;

    private String requiredPermission;

    private String method;

    private String path;

    private String summary;

    private String description;

    private List<OpenApiParamVO> queryParams;

    /** PUT/POST 请求体字段说明 */
    private List<OpenApiParamVO> bodyParams;

    /** 请求体 JSON 示例 */
    private Map<String, Object> requestBodyExample;

    /** 响应 JSON 示例 */
    private Map<String, Object> responseExample;

    private boolean allowed;
}
