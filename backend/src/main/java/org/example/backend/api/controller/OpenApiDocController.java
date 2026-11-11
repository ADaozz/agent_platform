package org.example.backend.api.controller;

import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.example.backend.api.service.OpenApiDocService;
import org.example.backend.common.result.AjaxResult;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/open")
public class OpenApiDocController {

    @Autowired
    private OpenApiDocService openApiDocService;

    @GetMapping("/doc")
    @RequiresPermissions("api:token:list")
    public AjaxResult doc() {
        return AjaxResult.success("成功", openApiDocService.getOpenApiDoc());
    }
}
