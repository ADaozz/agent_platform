package org.example.backend.asset.host.controller;

import org.example.backend.asset.host.dto.VmHostQueryDTO;
import org.example.backend.asset.host.dto.VmHostUpdateDTO;
import org.example.backend.asset.host.service.VmHostService;
import org.example.backend.common.annotation.Log;
import org.example.backend.common.enums.BusinessType;
import org.example.backend.common.result.AjaxResult;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import javax.validation.Valid;

/**
 * 虚机：全员可 list；仅 owner 可 update；不提供新增/删除接口。
 */
@RestController
@Validated
@RequestMapping("/asset/vm")
public class VmHostController {

    @Autowired
    private VmHostService vmHostService;

    @Log(title = "虚机管理", businessType = BusinessType.QUERY)
    @GetMapping
    public AjaxResult list(VmHostQueryDTO query) {
        return AjaxResult.success("成功", vmHostService.listVmHost(query));
    }

    @Log(title = "虚机管理", businessType = BusinessType.UPDATE)
    @PutMapping
    public AjaxResult update(@Valid @RequestBody VmHostUpdateDTO dto) {
        vmHostService.updateVmHost(dto);
        return AjaxResult.success("更新成功", null);
    }
}
