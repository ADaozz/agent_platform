package org.example.backend.system.permission.service;

import com.baomidou.mybatisplus.extension.service.IService;
import org.example.backend.common.vo.OptionVO;
import org.example.backend.common.vo.PageResultVO;
import org.example.backend.system.permission.dto.SysPermissionQueryDTO;
import org.example.backend.system.permission.entity.SysPermissionEntity;
import org.example.backend.system.permission.vo.SysPermissionVO;

import java.util.List;

public interface SysPermissionService extends IService<SysPermissionEntity> {
    SysPermissionEntity getByPermissionId(Long PermissionId);

    /** Shiro 鉴权用，返回权限标识字符串 */
    List<String> selectSysPermissionByUserId(Long userId);

    List<OptionVO> selectPermissionOptionsByUserId(Long userId);

    /** 多选框选项：全部权限 */
    List<OptionVO> listAllPermissionOptions();

    PageResultVO<SysPermissionVO> listPermissionInfo(SysPermissionQueryDTO dto);
}