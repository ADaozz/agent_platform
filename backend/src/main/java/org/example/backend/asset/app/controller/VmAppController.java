package org.example.backend.asset.app.controller;

import org.example.backend.asset.app.dto.VmAppQueryDTO;
import org.example.backend.asset.app.dto.VmAppUpdateDTO;
import org.example.backend.asset.app.service.VmAppService;
import org.example.backend.common.annotation.Log;
import org.example.backend.common.enums.BusinessType;
import org.example.backend.common.result.AjaxResult;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import javax.validation.Valid;

/**
 * 应用：全员可 list；仅虚机 owner 可 update；不提供新增/删除接口。
 */
@RestController
@Validated
@RequestMapping("/asset/app")
public class VmAppController {

    @Autowired
    private VmAppService vmAppService;

    @Log(title = "应用管理", businessType = BusinessType.QUERY)
    @GetMapping
    public AjaxResult list(VmAppQueryDTO query) {
        return AjaxResult.success("成功", vmAppService.listVmApp(query));
    }

    @Log(title = "应用管理", businessType = BusinessType.UPDATE)
    @PutMapping
    public AjaxResult update(@Valid @RequestBody VmAppUpdateDTO dto) {
        vmAppService.updateVmApp(dto);
        return AjaxResult.success("更新成功", null);
    }
}
