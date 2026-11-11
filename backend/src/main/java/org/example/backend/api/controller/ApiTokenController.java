package org.example.backend.api.controller;

import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.example.backend.api.dto.ApiTokenCreateDTO;
import org.example.backend.api.dto.ApiTokenQueryDTO;
import org.example.backend.api.service.ApiTokenService;
import org.example.backend.common.annotation.Log;
import org.example.backend.common.enums.BusinessType;
import org.example.backend.common.result.AjaxResult;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import javax.validation.Valid;

@RestController
@Validated
@RequestMapping("/api/token")
public class ApiTokenController {

    @Autowired
    private ApiTokenService apiTokenService;

    @Log(title = "API Token", businessType = BusinessType.QUERY)
    @GetMapping
    @RequiresPermissions("api:token:list")
    public AjaxResult list(ApiTokenQueryDTO query) {
        return AjaxResult.success("成功", apiTokenService.listApiToken(query));
    }

    @Log(title = "API Token", businessType = BusinessType.QUERY)
    @GetMapping("/user/{userId}")
    @RequiresPermissions("api:token:get")
    public AjaxResult get(@PathVariable Long userId) {
        return AjaxResult.success("成功", apiTokenService.getApiToken(userId));
    }

    @Log(title = "API Token", businessType = BusinessType.QUERY, isSaveResponseData = false)
    @GetMapping("/grantOptions")
    @RequiresPermissions("api:token:add")
    public AjaxResult grantOptions() {
        return AjaxResult.success("成功", apiTokenService.listGrantOptions());
    }

    @Log(title = "API Token", businessType = BusinessType.INSERT)
    @PostMapping
    @RequiresPermissions("api:token:add")
    public AjaxResult add(@Valid @RequestBody ApiTokenCreateDTO dto) {
        return AjaxResult.success("新增成功", apiTokenService.createApiToken(dto));
    }

    @Log(title = "API Token", businessType = BusinessType.DELETE)
    @DeleteMapping("/{tokenId}")
    @RequiresPermissions("api:token:delete")
    public AjaxResult delete(@PathVariable String tokenId) {
        apiTokenService.deleteApiToken(tokenId);
        return AjaxResult.success("删除成功", null);
    }
}
