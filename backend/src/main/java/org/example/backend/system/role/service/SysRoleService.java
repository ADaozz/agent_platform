package org.example.backend.system.role.service;

import com.baomidou.mybatisplus.extension.service.IService;
import org.example.backend.common.vo.OptionVO;
import org.example.backend.common.vo.PageResultVO;
import org.example.backend.system.role.dto.SysRoleCreateDTO;
import org.example.backend.system.role.dto.SysRolePermAssignDTO;
import org.example.backend.system.role.dto.SysRoleQueryDTO;
import org.example.backend.system.role.dto.SysRoleUpdateDTO;
import org.example.backend.system.role.entity.SysRoleEntity;
import org.example.backend.system.role.vo.SysRoleVO;

import java.util.List;

public interface SysRoleService extends IService<SysRoleEntity> {

    SysRoleEntity getByRoleId(Long roleId);

    List<String> selectSysRoleByUserId(Long userId);

    List<OptionVO> selectRoleOptionsByUserId(Long userId);

    List<OptionVO> listAllRoleOptions();

    PageResultVO<SysRoleVO> listRoleInfo(SysRoleQueryDTO dto);

    void createRole(SysRoleCreateDTO dto);

    void updateRole(SysRoleUpdateDTO dto);

    void deleteRole(Long roleId);

    void assignRolePermissions(SysRolePermAssignDTO dto);
}
