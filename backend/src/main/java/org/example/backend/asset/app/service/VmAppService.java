package org.example.backend.asset.app.service;

import com.baomidou.mybatisplus.extension.service.IService;
import org.example.backend.asset.app.dto.VmAppQueryDTO;
import org.example.backend.asset.app.dto.VmAppUpdateDTO;
import org.example.backend.asset.app.entity.VmAppEntity;
import org.example.backend.asset.app.vo.VmAppVO;
import org.example.backend.common.vo.PageResultVO;

public interface VmAppService extends IService<VmAppEntity> {

    PageResultVO<VmAppVO> listVmApp(VmAppQueryDTO dto);

    void updateVmApp(VmAppUpdateDTO dto);
}
