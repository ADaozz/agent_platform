package org.example.backend.api.service.impl;

import org.apache.shiro.SecurityUtils;
import org.apache.shiro.subject.Subject;
import org.example.backend.api.constant.OpenApiDocCatalog;
import org.example.backend.api.service.OpenApiDocService;
import org.example.backend.api.vo.OpenApiAuthHeaderVO;
import org.example.backend.api.vo.OpenApiAuthVO;
import org.example.backend.api.vo.OpenApiDocVO;
import org.example.backend.api.vo.OpenApiOperationVO;
import org.example.backend.common.exception.BusinessException;
import org.example.backend.common.exception.Module;
import org.example.backend.security.context.LoginUserUtils;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

@Service
public class OpenApiDocServiceImpl implements OpenApiDocService {

    @Override
    // 获取当前用户可访问的OpenAPI文档
    public OpenApiDocVO getOpenApiDoc() {
        Long userId = LoginUserUtils.getUserId();
        if (userId == null) {
            throw new BusinessException(Module.ModuleType.AUTH, "未登录", null);
        }
        Subject subject = SecurityUtils.getSubject();

        List<OpenApiOperationVO> operations = new ArrayList<>();
        for (OpenApiDocCatalog.Entry entry : OpenApiDocCatalog.implementedEntries()) {
            if (!subject.isPermitted(entry.getRequiredPermission())) {
                continue;
            }
            operations.add(toOperationVO(entry, true));
        }

        OpenApiDocVO doc = new OpenApiDocVO();
        doc.setBaseUrl("/api");
        doc.setAuth(buildAuth());
        doc.setOperations(operations);
        return doc;
    }

    // 构建API认证说明
    private OpenApiAuthVO buildAuth() {
        OpenApiAuthHeaderVO ak = new OpenApiAuthHeaderVO();
        ak.setName("X-Access-Key");
        ak.setRequired(true);
        OpenApiAuthHeaderVO sk = new OpenApiAuthHeaderVO();
        sk.setName("X-Secret-Key");
        sk.setRequired(true);

        OpenApiAuthVO auth = new OpenApiAuthVO();
        auth.setType("AK_SK");
        auth.setHeaders(Arrays.asList(ak, sk));
        auth.setNote("外部系统调用须携带 AK/SK；平台内调试可选用登录 JWT 或 AK/SK");
        return auth;
    }

    // 将目录条目转换为接口VO
    private OpenApiOperationVO toOperationVO(OpenApiDocCatalog.Entry entry, boolean allowed) {
        OpenApiOperationVO vo = new OpenApiOperationVO();
        vo.setId(entry.getId());
        vo.setGroupKey(entry.getGroupKey());
        vo.setGroupName(entry.getGroupName());
        vo.setGrant(entry.getGrant());
        vo.setRequiredPermission(entry.getRequiredPermission());
        vo.setMethod(entry.getMethod());
        vo.setPath(entry.getPath());
        vo.setSummary(entry.getSummary());
        vo.setDescription(entry.getDescription());
        vo.setQueryParams(entry.getQueryParams());
        vo.setBodyParams(entry.getBodyParams());
        vo.setRequestBodyExample(entry.getRequestBodyExample());
        vo.setResponseExample(entry.getResponseExample());
        vo.setAllowed(allowed);
        return vo;
    }
}
