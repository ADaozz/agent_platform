package org.example.backend.system.role.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.example.backend.common.vo.OptionVO;
import org.example.backend.system.role.entity.SysRoleEntity;

import java.util.List;

public interface SysRoleMapper extends BaseMapper<SysRoleEntity> {

    @Select("SELECT DISTINCT r.sys_role " +
            "FROM sys_user_role ur " +
            "JOIN sys_role r ON ur.role_id = r.role_id " +
            "WHERE ur.user_id = #{userId}")
    List<String> selectSysRoleByUserId(@Param("userId") Long userId);

    @Select("SELECT DISTINCT r.role_id AS id, r.sys_role AS label " +
            "FROM sys_user_role ur " +
            "JOIN sys_role r ON ur.role_id = r.role_id " +
            "WHERE ur.user_id = #{userId}")
    List<OptionVO> selectRoleOptionsByUserId(@Param("userId") Long userId);

    @Select("SELECT role_id AS id, sys_role AS label " +
            "FROM sys_role ORDER BY role_id")
    List<OptionVO> selectAllRoleOptions();
}
